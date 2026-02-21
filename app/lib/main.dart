import 'package:flutter/material.dart';
import 'package:flutter_ai_toolkit/flutter_ai_toolkit.dart';

import 'langgraph_provider.dart';

void main() {
  runApp(const StatsAgentApp());
}

class StatsAgentApp extends StatelessWidget {
  const StatsAgentApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stats Agent',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: const ChatPage(),
    );
  }
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  late final LangGraphProvider _provider;

  @override
  void initState() {
    super.initState();
    _provider = LangGraphProvider(
      baseUrl: 'http://127.0.0.1:2024',
      assistantId: 'agent',
    );
  }

  @override
  void dispose() {
    _provider.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Stats Agent Chat')),
      body: LlmChatView(
        provider: _provider,
        welcomeMessage: 'Ask me anything about stats.',
        suggestions: const [
          'Explain p-value vs confidence interval.',
          'When should I use logistic regression?',
          'Give me a quick A/B test checklist.',
        ],
      ),
    );
  }
}
