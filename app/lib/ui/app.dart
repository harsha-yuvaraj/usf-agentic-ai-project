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
      title: 'Multi-Agent System for Statistical Data Analysis and Clinical Trials',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorSchemeSeed: Colors.indigo,
        useMaterial3: true,
      ),
      home: Scaffold(
        appBar: AppBar(
          title: const Text("Multi-Agent System for Statistical Data Analysis and Clinical Trials"),
          elevation: 2,
        ),
        body: Consumer<LangGraphProvider>(
          builder: (_, provider, _) => Stack(
            children: [
              LlmChatView(
                provider: provider,
                welcomeMessage: 'Welcome! Upload your dataset and let our system crunch the numbers.',
                suggestions: const [
                  'Summarize the key statistics for my uploaded dataset.',
                  'Perform a t-test to compare groups in this clinical trial.',
                  'Identify any significant trends or outliers in the data.',
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
              if (provider.currentAgentState != null)
                Positioned(
                  bottom: 90,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      curve: Curves.easeInOut,
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.primaryContainer,
                        borderRadius: BorderRadius.circular(24),
                        boxShadow: const [
                          BoxShadow(
                            color: Colors.black12,
                            blurRadius: 8,
                            offset: Offset(0, 4),
                          )
                        ],
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Theme.of(context).colorScheme.onPrimaryContainer,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            provider.currentAgentState!,
                            style: TextStyle(
                              color: Theme.of(context).colorScheme.onPrimaryContainer,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
