import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:flutter_ai_toolkit/flutter_ai_toolkit.dart';

import 'package:firebase_core/firebase_core.dart';

import 'firebase_options.dart';
import 'langgraph_provider.dart';



void main() async {
    WidgetsFlutterBinding.ensureInitialized();
    await Firebase.initializeApp(
      options: DefaultFirebaseOptions.currentPlatform,
    );

    await FirebaseStorage.instance.useStorageEmulator('localhost', 9199);

    runApp(StatsAgentApp(storage: FirebaseStorage.instance));
  }

class StatsAgentApp extends StatelessWidget {
  const StatsAgentApp({super.key, required this.storage});

  final FirebaseStorage storage;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stats Agent',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: ChatPage(storage: FirebaseStorage.instance),
    );
  }
}

class ChatPage extends StatefulWidget {
  const ChatPage({super.key, required this.storage});

  final FirebaseStorage storage;

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
      storage: widget.storage,
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
