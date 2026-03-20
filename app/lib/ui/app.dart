import 'package:flutter/material.dart';
import 'package:flutter_ai_toolkit/flutter_ai_toolkit.dart';
import 'package:provider/provider.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../providers/langgraph_provider.dart';
import 'charting/image_carousel.dart';

class App extends StatelessWidget {
  const App({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Stats Agent',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
      ),
      home: Scaffold(
        appBar: AppBar(
          title: const Text("Stats Agent"),
          elevation: 2,
        ),
        body: Consumer<LangGraphProvider>(
          builder: (_, provider, _) => LlmChatView(
            provider: provider,
            welcomeMessage: 'Ask me anything about stats.',
            suggestions: const [
              'Summarize the columns in test_clinical_trial.csv',
              'Plot BP_Before vs BP_After by Group.',
              'Is there a significant difference in BP drop?',
            ],
            responseBuilder: (context, response) {
              final images = provider.getImagesForText(response);
              
              // Strip the hidden gallery marker for clean text rendering
              final markerIndex = response.lastIndexOf('\u200B');
              final cleanResponse = markerIndex != -1 
                  ? response.substring(0, markerIndex) 
                  : response;
              
              return Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  MarkdownBody(
                    data: cleanResponse,
                    selectable: false,
                    onTapLink: (_, href, __) {
                      if (href != null) launchUrl(Uri.parse(href));
                    },
                  ),
                  if (images.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    const Divider(height: 1),
                    const SizedBox(height: 16),
                    ImageCarousel(images: images),
                  ],
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}
