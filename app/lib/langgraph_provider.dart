import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_ai_toolkit/flutter_ai_toolkit.dart';
import 'package:http/http.dart' as http;

import 'package:firebase_storage/firebase_storage.dart';

/// LlmProvider implementation backed by a LangGraph local/dev server.
/// Works with LlmChatView without FirebaseProvider.
class LangGraphProvider extends LlmProvider with ChangeNotifier {
  LangGraphProvider({
    required this.baseUrl,
    required FirebaseStorage storage,
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
    return _runPrompt(prompt: prompt, attachments: attachments, persistHistory: false);
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

    yield* stream.map((chunk) {
      llmMessage.append(chunk);
      return chunk;
    });

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
        'attachments': await _handleAttachments(attachments)
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
    final text = _extractText(decoded);

    if (text.isEmpty) {
      yield 'No response from LangGraph.';
      return;
    }

    yield text;
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

Future<String> _uploadAttachment(Attachment attachment) async{
    if (attachment is FileAttachment) {
      final ref = _storage.ref().child('attachments/${attachment.name}');
      await ref.putData(attachment.bytes, SettableMetadata(contentType: attachment.mimeType));

      return 'attachments/${attachment.name}';
    } else if (attachment is LinkAttachment) {
      return attachment.url.toString();
    } else {
      throw Exception('Unsupported attachment type: ${attachment.runtimeType}');
    }
  }

  Future<List> _handleAttachments(Iterable<Attachment> attachments) async {
    if (attachments.isEmpty) return [];

    final summaries = await Future.wait(
      attachments.map((a) async {
        final path = await _uploadAttachment(a);
        return path;
      }),
    );

    return summaries;

  }
  String _extractText(dynamic responseJson) {
    if (responseJson is! Map<String, dynamic>) return '';

    final messages = responseJson['messages'];
    if (messages is! List) return '';

    for (var i = messages.length - 1; i >= 0; i--) {
      final m = messages[i];
      if (m is! Map<String, dynamic>) continue;

      final role = m['role']?.toString(); // optional
      final type = m['type']?.toString(); // LangGraph/LangChain
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


  @override
  void dispose() {
    _client.close();
    super.dispose();
  }
}
