import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'image_widget.dart';

class ImagesWidget extends StatefulWidget {
  const ImagesWidget({super.key, required this.images});

  final List<Uint8List> images;

  @override
  State<ImagesWidget> createState() => _ImagesWidgetState();
}

class _ImagesWidgetState extends State<ImagesWidget> {
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.images.isEmpty) {
      return const SizedBox.shrink();
    }

    return SizedBox(
      height: 380,
      width: double.infinity,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Scrollbar(
          controller: _scrollController,
          thumbVisibility: true,
          interactive: true,
          child: SingleChildScrollView(
            controller: _scrollController,
            scrollDirection: Axis.horizontal,
            child: Row(
              children: widget.images
                  .map((b) => ImageWidget(bytes: b))
                  .toList(),
            ),
          ),
        ),
      ),
    );
  }
}