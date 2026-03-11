import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';

import 'firebase_options.dart';
import 'langgraph_provider.dart';
import 'ui/app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  await FirebaseStorage.instance.useStorageEmulator('localhost', 9199);

  runApp(ChangeNotifierProvider(
    create: (_) => LangGraphProvider(
      baseUrl: 'http://127.0.0.1:2024',
      assistantId: 'agent',
      storage: FirebaseStorage.instance,
      ),
    child: const App(),
    )
  );
}