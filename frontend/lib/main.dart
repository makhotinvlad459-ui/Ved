// frontend/lib/main.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/home_screen.dart';
import 'screens/upload_screen.dart';
import 'services/api_service.dart';
import 'screens/packing_list_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Provider(
      create: (_) => ApiService(),
      child: MaterialApp(
        title: 'VED Excel Processor',
        theme: ThemeData(
          primarySwatch: Colors.blue,
          useMaterial3: true,
          fontFamily: 'SF Pro Display',
        ),
        home: const HomeScreen(),
        debugShowCheckedModeBanner: false,
        routes: {
          '/upload': (context) => const UploadScreen(),
          '/packing-list': (context) => const PackingListScreen(), 
        },
      ),
    );
  }
}