import 'dart:typed_data';

import 'package:flutter/material.dart';

import 'image_widget.dart';

class ImagesWidget extends StatelessWidget {
  const ImagesWidget({super.key, required this.images});

  final List<Uint8List> images;

  @override
  Widget build(BuildContext context) {
    if (images.isNotEmpty) {
        return Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: 
                images.map((b) => ImageWidget(bytes: b)).toList(),
            )
          ));
      }
      else {
        return SizedBox.shrink();
      }
    }
  }
