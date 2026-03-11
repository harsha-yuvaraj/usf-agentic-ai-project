import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_ai_toolkit/flutter_ai_toolkit.dart';
import 'package:http/http.dart' as http;

import 'package:firebase_storage/firebase_storage.dart';
import 'package:logger/logger.dart';

class LangGraphProvider extends LlmProvider with ChangeNotifier {
  LangGraphProvider({
    required FirebaseStorage storage,
    this.baseUrl = 'http://127.0.0.1:2024',
    this.assistantId = 'agent',
    this.apiKey,
    Iterable<ChatMessage>? history,
    String? threadId,
    http.Client? httpClient,
  }) : _history = List<ChatMessage>.from(history ?? []),
       _threadId = threadId,
       _client = httpClient ?? http.Client(),
       _storage = storage;

  final String baseUrl;
  final String assistantId;
  final String? apiKey;
  final http.Client _client;
  final FirebaseStorage _storage;

  final List<ChatMessage> _history;
  String? _threadId;

  final List<Uint8List> _images = [];
  List<Uint8List> get images => List.unmodifiable(_images);

  @override
  Iterable<ChatMessage> get history => _history;

  @override
  set history(Iterable<ChatMessage> history) {
    _history
      ..clear()
      ..addAll(history);
    notifyListeners();
  }

  @override
  Stream<String> generateStream(
    String prompt, {
    Iterable<Attachment> attachments = const [],
  }) {
    return _runPrompt(
      prompt: prompt,
      attachments: attachments,
      persistHistory: false,
    );
  }

  @override
  Stream<String> sendMessageStream(
    String prompt, {
    Iterable<Attachment> attachments = const [],
  }) async* {
    final userMessage = ChatMessage.user(prompt, attachments);
    final llmMessage = ChatMessage.llm();

    _history.addAll([userMessage, llmMessage]);
    notifyListeners();

    final stream = _runPrompt(
      prompt: prompt,
      attachments: attachments,
      persistHistory: true,
    );

    await for (final chunk in stream) {
      if (chunk.isNotEmpty) {
        llmMessage.append(chunk);
        yield chunk;
      }
    }

    notifyListeners();
  }

  Stream<String> _runPrompt({
    required String prompt,
    required Iterable<Attachment> attachments,
    required bool persistHistory,
  }) async* {
    final threadId = await _ensureThread();
    final uri = Uri.parse('$baseUrl/threads/$threadId/runs/wait');

    final payload = <String, dynamic>{
      'assistant_id': assistantId,
      'input': {
        'messages': [
          {
            'role': 'user',
            'content': prompt,
          },
        ],
        'file_names': await _handleAttachments(attachments),
      },
    };

    final response = await _client.post(
      uri,
      headers: _headers,
      body: jsonEncode(payload),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'LangGraph request failed (${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body);
    final parsed = _parseResponse(decoded);

    if (parsed.images.isNotEmpty) {
      _images
        ..clear()
        ..addAll(parsed.images);
      notifyListeners();
    }

    if (parsed.text.isEmpty && parsed.images.isEmpty) {
      yield 'No response from LangGraph.';
      return;
    }

    if (parsed.text.isNotEmpty) {
      yield parsed.text;
    }
  }

  Future<String> _ensureThread() async {
    if (_threadId != null && _threadId!.isNotEmpty) return _threadId!;

    final response = await _client.post(
      Uri.parse('$baseUrl/threads'),
      headers: _headers,
      body: jsonEncode({}),
    );

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception(
        'Failed to create thread (${response.statusCode}): ${response.body}',
      );
    }

    final decoded = jsonDecode(response.body) as Map<String, dynamic>;
    final id = decoded['thread_id'] as String?;
    if (id == null || id.isEmpty) {
      throw Exception('LangGraph did not return thread_id.');
    }

    _threadId = id;
    return id;
  }

  Map<String, String> get _headers {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (apiKey != null && apiKey!.isNotEmpty) {
      headers['x-api-key'] = apiKey!;
    }
    return headers;
  }

  Future<void> _uploadAttachment(Attachment attachment) async {
    if (attachment is FileAttachment) {
      final ref = _storage.ref().child('attachments/${attachment.name}');
      await ref.putData(
        attachment.bytes,
        SettableMetadata(contentType: attachment.mimeType),
      );
    } else if (attachment is LinkAttachment) {
      Logger().d('Link attachment: ${attachment.url}');
    } else {
      throw Exception('Unsupported attachment type: ${attachment.runtimeType}');
    }
  }

  Future<List<String>> _handleAttachments(
    Iterable<Attachment> attachments,
  ) async {
    if (attachments.isEmpty) return [];

    final summaries = await Future.wait(
      attachments.map((a) async {
        await _uploadAttachment(a);
        Logger().d('Uploaded attachment: ${a.name}');
        return a.name;
      }),
    );

    return summaries;
  }

  _ParsedResponse _parseResponse(dynamic responseJson) {
    if (responseJson is! Map<String, dynamic>) {
      return const _ParsedResponse(text: '', images: []);
    }

    final text = _extractText(responseJson);
    final images = _extractImages(responseJson);

    Logger().d('LangGraph returned ${images.length} image(s).');

    return _ParsedResponse(text: text, images: images);
  }

  String _extractText(Map<String, dynamic> responseJson) {
    final messages = responseJson['messages'];
    if (messages is! List) return '';

    for (var i = messages.length - 1; i >= 0; i--) {
      final m = messages[i];
      if (m is! Map<String, dynamic>) continue;

      final role = m['role']?.toString();
      final type = m['type']?.toString();
      final isAssistant = role == 'assistant' || role == 'ai' || type == 'ai';
      if (!isAssistant) continue;

      final content = m['content'];
      if (content is String) return content.trim();

      if (content is List) {
        final buffer = StringBuffer();
        for (final part in content) {
          if (part is String) {
            buffer.write(part);
          } else if (part is Map) {
            final text = part['text'];
            if (text is String) buffer.write(text);
          }
        }
        final out = buffer.toString().trim();
        if (out.isNotEmpty) return out;
      }
    }

    return '';
  }

  List<Uint8List> _extractImages(Map<String, dynamic> responseJson) {
    final rawImages = responseJson['images'];
    if (rawImages == null) return [];

    final images = <Uint8List>[];

    if (rawImages is List) {
      for (final raw in rawImages) {
        final bytes = _parseSingleImage(raw);
        if (bytes != null) {
          images.add(bytes);
        }
      }
    } else {
      final bytes = _parseSingleImage(rawImages);
      if (bytes != null) {
        images.add(bytes);
      }
    }

    return images;
  }

  Uint8List? _parseSingleImage(dynamic raw) {
    try {
      String? base64Data;

      if (raw is String) {
        final parsed = _splitDataUrl(raw);
        base64Data = parsed.base64;
      } else if (raw is Map<String, dynamic>) {
        final dataCandidate =
            raw['base64'] ??
            raw['data'] ??
            raw['image'] ??
            raw['image_base64'];

        if (dataCandidate is! String) return null;

        final parsed = _splitDataUrl(dataCandidate);
        base64Data = parsed.base64;
      } else {
        return null;
      }

      if (base64Data.isEmpty) return null;

      return base64Decode(_normalizeBase64(base64Data));
    } catch (e) {
      Logger().e('Failed to decode image', error: e);
      return null;
    }
  }

  _DataUrlParts _splitDataUrl(String value) {
    final trimmed = value.trim();

    final match = RegExp(
      r'^data:([^;]+);base64,(.*)$',
      dotAll: true,
    ).firstMatch(trimmed);

    if (match != null) {
      return _DataUrlParts(
        mimeType: match.group(1),
        base64: match.group(2) ?? '',
      );
    }

    return _DataUrlParts(mimeType: null, base64: trimmed);
  }

  String _normalizeBase64(String input) {
    final sanitized = input.replaceAll(RegExp(r'\s+'), '');
    final remainder = sanitized.length % 4;
    if (remainder == 0) return sanitized;
    return sanitized.padRight(sanitized.length + (4 - remainder), '=');
  }

  @override
  void dispose() {
    _client.close();
    super.dispose();
  }
}

class _ParsedResponse {
  const _ParsedResponse({
    required this.text,
    required this.images,
  });

  final String text;
  final List<Uint8List> images;
}

class _DataUrlParts {
  const _DataUrlParts({
    required this.mimeType,
    required this.base64,
  });

  final String? mimeType;
  final String base64;
}