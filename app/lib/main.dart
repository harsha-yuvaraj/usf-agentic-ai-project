import 'package:firebase_storage/firebase_storage.dart';
import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'firebase_options.dart';
import 'providers/langgraph_provider.dart';
import 'ui/app.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: ".env");

  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );

  final storageHost = dotenv.env['FIREBASE_STORAGE_EMULATOR_HOST'] ?? 'localhost';
  final storagePort = int.tryParse(dotenv.env['FIREBASE_STORAGE_EMULATOR_PORT'] ?? '9199') ?? 9199;
  await FirebaseStorage.instance.useStorageEmulator(storageHost, storagePort);

  final prefs = await SharedPreferences.getInstance();
  final threadId = prefs.getString('langgraph_thread_id');

  runApp(ChangeNotifierProvider(
    create: (_) => LangGraphProvider(
      baseUrl: dotenv.env['LANGGRAPH_URL'] ?? 'http://127.0.0.1:2024',
      assistantId: 'agent',
      storage: FirebaseStorage.instance,
      threadId: threadId,
      ),
    child: const App(),
    )
  );
}