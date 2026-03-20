import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:photo_view/photo_view.dart';

class FullscreenViewer extends StatelessWidget {
  final Uint8List bytes;
  final String? title;

  const FullscreenViewer({super.key, required this.bytes, this.title});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: Colors.black,
        iconTheme: const IconThemeData(color: Colors.white),
        title: Text(title ?? 'Chart Viewer', style: const TextStyle(color: Colors.white)),
        actions: [
          IconButton(
            icon: const Icon(Icons.download),
            onPressed: () {
              // TODO: Implement image saving
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Saving to gallery not yet implemented')),
              );
            },
          ),
        ],
      ),
      body: Hero(
        tag: bytes.hashCode.toString(),
        child: PhotoView(
          imageProvider: MemoryImage(bytes),
          minScale: PhotoViewComputedScale.contained,
          maxScale: PhotoViewComputedScale.covered * 2,
          backgroundDecoration: const BoxDecoration(color: Colors.black),
        ),
      ),
    );
  }
}
