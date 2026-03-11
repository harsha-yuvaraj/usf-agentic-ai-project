import 'package:flutter/material.dart';
import 'package:flutter_ai_toolkit/flutter_ai_toolkit.dart';
import 'package:provider/provider.dart';

import '../langgraph_provider.dart';
import 'charting/images_widget.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stats Agent',
      theme: ThemeData(colorSchemeSeed: Colors.indigo, useMaterial3: true),
      home: Scaffold(
        appBar: AppBar(title: Text("Stats Agent")),
        body: Consumer<LangGraphProvider>(
          builder: (_, provider, _) => Column(
            children: [
              ImagesWidget(images: provider.images),
              Expanded(
                child: LlmChatView(
                  provider: provider,
                  welcomeMessage: 'Ask me anything about stats.',
                  suggestions: const [
                    'Explain p-value vs confidence interval.',
                    'When should I use logistic regression?',
                    'Give me a quick A/B test checklist.',
                  ],
                )
              )
            ],
          )
        ),
      ),
    );
  }
}
