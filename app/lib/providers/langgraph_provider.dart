import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_ai_toolkit/flutter_ai_toolkit.dart';
import 'package:http/http.dart' as http;
import 'package:firebase_storage/firebase_storage.dart';
import 'package:logger/logger.dart';
import 'package:shared_preferences/shared_preferences.dart';

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

  // We are removing the global _images list and instead attaching images 
  // directly to the chat history to provide contextual rendering.
  // Note: flutter_ai_toolkit supports attachments via ChatMessage.user(..., attachments)
  // For AI messages, we can append markdown images if they are base64 strings.

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
    return _runPromptStream(
      prompt: prompt,
      attachments: attachments,
      llmMessage: ChatMessage.llm(),
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

    try {
      final stream = _runPromptStream(
        prompt: prompt,
        attachments: attachments,
        llmMessage: llmMessage,
      );

      await for (final chunk in stream) {
        if (chunk.isNotEmpty) {
          llmMessage.append(chunk);
          yield chunk;
        }
      }
    } catch (e, st) {
      Logger().e('Error in sendMessageStream', error: e, stackTrace: st);
      final errorMsg = '\n\n**Error:** An issue occurred while communicating with the agent. Please try again.';
      llmMessage.append(errorMsg);
      yield errorMsg;
    }

    notifyListeners();
  }

  Stream<String> _runPromptStream({
    required String prompt,
    required Iterable<Attachment> attachments,
    required ChatMessage llmMessage,
  }) async* {
    final threadId = await _ensureThread();
    final uri = Uri.parse('$baseUrl/threads/$threadId/runs/stream');

    final payload = <String, dynamic>{
      'assistant_id': assistantId,
      'input': {
        'messages': [
          {
            'role': 'user',
            'content': prompt,
          },
        ],
        'attachments': await _handleAttachments(attachments),
      },
      'stream_mode': ['values', 'messages'],
    };

    final request = http.Request('POST', uri)
      ..headers.addAll(_headers)
      ..body = jsonEncode(payload);

    final response = await _client.send(request);

    if (response.statusCode < 200 || response.statusCode >= 300) {
      final body = await response.stream.bytesToString();
      throw Exception('LangGraph stream failed (${response.statusCode}): $body');
    }

    final stream = response.stream.transform(utf8.decoder).transform(const LineSplitter());

    String event = '';
    String dataBuffer = '';
    final seenImageHashes = <int>{};
    String accumulatedAiText = '';
    final signaledToolCallIds = <String>{};

    await for (final line in stream) {
      if (line.startsWith(':')) {
        // Ignore SSE comments/heartbeats (e.g., ": heartbeat")
        continue;
      } else if (line.startsWith('event: ')) {
        event = line.substring(7).trim();
      } else if (line.startsWith('data: ')) {
        dataBuffer += line.substring(6).trim();
      } else if (line.isEmpty) {
        if (dataBuffer.isNotEmpty && dataBuffer != 'null') {
          try {
            final dataJson = jsonDecode(dataBuffer);

            // Handle token-by-token messages
            if (event == 'messages/partial') {
              if (dataJson is List && dataJson.isNotEmpty) {
                final msgChunk = dataJson[0];
                if (msgChunk is Map<String, dynamic> && (msgChunk['role'] == 'ai' || msgChunk['type'] == 'ai' || msgChunk['type'] == 'AIMessageChunk')) {
                  
                  // Check if the agent is calling a tool dynamically
                  if (msgChunk['tool_calls'] != null && (msgChunk['tool_calls'] as List).isNotEmpty) {
                    for (final tool in msgChunk['tool_calls']) {
                      if (tool is Map<String, dynamic>) {
                        final toolId = tool['id']?.toString() ?? '';
                        final toolName = tool['name']?.toString() ?? 'tool';
                        
                        if (toolId.isNotEmpty && !signaledToolCallIds.contains(toolId)) {
                           signaledToolCallIds.add(toolId);
                           
                           String actionText = 'using $toolName';
                           if (toolName == 'execute_code') {
                              actionText = 'executing code';
                           } else if (toolName == 'search') {
                              actionText = 'searching the web';
                           }
                           
                           yield '\n\n> ⏳ *Agent is $actionText...*\n\n';
                        }
                      }
                    }
                  }

                  final content = msgChunk['content'];
                  String newText = '';

                  if (content is String && content.isNotEmpty) {
                    newText = content;
                  } else if (content is List) {
                    for (final part in content) {
                      if (part is String) {
                        newText += part;
                      } else if (part is Map && part['text'] is String) {
                        newText += part['text'];
                      }
                    }
                  }

                  if (newText.isNotEmpty) {
                    // Smart diffing: handle both cumulative payloads and delta payloads
                    if (accumulatedAiText.isNotEmpty && newText.startsWith(accumulatedAiText)) {
                      // Backend sent a cumulative string
                      final delta = newText.substring(accumulatedAiText.length);
                      if (delta.isNotEmpty) {
                        yield delta;
                        accumulatedAiText = newText;
                      }
                    } else if (newText != accumulatedAiText) {
                      // Backend sent a delta chunk (or completely new text)
                      // Edge case: if we get the exact same chunk, we ignore it.
                      // Otherwise, we yield it and append it to our tracker.
                    
                      yield newText;
                      accumulatedAiText += newText;
                    }
                    
                    // Small delay to allow the Flutter UI thread to render and prevent scrolling freezes
                    await Future.delayed(const Duration(milliseconds: 10));
                  }
                }
              }
            } 
            // Handle updates to extract the images generated by the tool
            else if (event == 'updates' || event == 'values') {
               final stateData = (event == 'updates') ? (dataJson is Map && dataJson.containsKey('tools') ? dataJson['tools'] : dataJson) : dataJson;
               if (stateData is Map<String, dynamic>) {
                 final images = _extractImages(stateData);
                 for (final img in images) {
                   final hash = img.base64.hashCode;
                   if (!seenImageHashes.contains(hash)) {
                      seenImageHashes.add(hash);
                      // Append image using markdown base64 inline so it renders in the chat bubble correctly
                      final markdownImage = '\n\n![Generated Chart](data:${img.mimeType ?? 'image/png'};base64,${img.base64})\n\n';
                      yield markdownImage;
                      await Future.delayed(const Duration(milliseconds: 50)); // Larger delay for images
                   }
                 }
               }
            }

          } catch (e) {
            Logger().w('Failed to parse SSE data chunk', error: e);
          }
        }
        event = '';
        dataBuffer = '';
      } else {
        // Multi-line data handling
        dataBuffer += line;
      }
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
    
    // Save to shared_preferences for thread persistence
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('langgraph_thread_id', id);
    } catch (e) {
      Logger().w('Failed to save thread ID to shared preferences', error: e);
    }

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

  List<_DataUrlParts> _extractImages(Map<String, dynamic> responseJson) {
    final rawImages = responseJson['images'];
    if (rawImages == null) return [];

    final images = <_DataUrlParts>[];

    if (rawImages is List) {
      for (final raw in rawImages) {
        final parts = _parseSingleImage(raw);
        if (parts != null && parts.base64.isNotEmpty) {
          images.add(parts);
        }
      }
    } else {
      final parts = _parseSingleImage(rawImages);
      if (parts != null && parts.base64.isNotEmpty) {
        images.add(parts);
      }
    }

    return images;
  }

  _DataUrlParts? _parseSingleImage(dynamic raw) {
    try {
      if (raw is String) {
        return _splitDataUrl(raw);
      } else if (raw is Map<String, dynamic>) {
        final dataCandidate =
            raw['base64'] ??
            raw['data'] ??
            raw['image'] ??
            raw['image_base64'];

        if (dataCandidate is String) {
          return _splitDataUrl(dataCandidate);
        }
      }
      return null;
    } catch (e) {
      Logger().e('Failed to parse image', error: e);
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
        base64: _normalizeBase64(match.group(2) ?? ''),
      );
    }

    return _DataUrlParts(mimeType: null, base64: _normalizeBase64(trimmed));
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

class _DataUrlParts {
  const _DataUrlParts({
    required this.mimeType,
    required this.base64,
  });

  final String? mimeType;
  final String base64;
}