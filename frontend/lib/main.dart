import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'screens/home_screen.dart';
import 'screens/upload_screen.dart';
import 'screens/packing_list_screen.dart';
import 'screens/cz_upload_screen.dart';
import 'screens/commercial_offer_screen.dart';
import 'screens/cz_codes_screen.dart';
import 'screens/products_screen.dart';
import 'screens/cz_cards_screen.dart';
import 'screens/cz_products_screen.dart';
import 'screens/cz_colors_screen.dart';
import 'screens/for_alice_screen.dart';
import 'services/api_service.dart';
import 'services/theme_provider.dart';
import 'screens/declaration_screen.dart';
import 'screens/far_east_screen.dart';
import 'screens/ai_assistant_screen.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        Provider<ApiService>(create: (_) => ApiService()),
        ChangeNotifierProvider<ThemeProvider>(create: (_) => ThemeProvider()),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, themeProvider, _) {
          return MaterialApp(
            title: 'VED Processor',
            debugShowCheckedModeBanner: false,

            // ============================================================
            // СВЕТЛАЯ ТЕМА
            // ============================================================
            theme: ThemeData(
              useMaterial3: true,
              brightness: Brightness.light,
              primarySwatch: Colors.blue,
              scaffoldBackgroundColor: const Color(0xFFF5F6F8),
              appBarTheme: const AppBarTheme(
                backgroundColor: Colors.white,
                foregroundColor: Colors.black,
                elevation: 0,
              ),
              cardColor: Colors.white,
              dialogBackgroundColor: Colors.white,
            ),

            // ============================================================
            // ТЕМНАЯ ТЕМА
            // ============================================================
            darkTheme: ThemeData(
              useMaterial3: true,
              brightness: Brightness.dark,
              primarySwatch: Colors.blue,
              scaffoldBackgroundColor: const Color(0xFF121212),
              appBarTheme: const AppBarTheme(
                backgroundColor: Color(0xFF1E1E1E),
                foregroundColor: Colors.white,
                elevation: 0,
              ),
              cardColor: const Color(0xFF1E1E1E),
              dialogBackgroundColor: const Color(0xFF2C2C2C),
              dividerColor: Colors.grey.shade800,
            ),

            themeMode: themeProvider.themeMode,

            home: const HomeScreen(),
            routes: {
              '/home': (context) => const HomeScreen(),
              '/upload': (context) => const UploadScreen(),
              '/packing-list': (context) => const PackingListScreen(),
              '/cz-upload': (context) => const CzUploadScreen(),
              '/commercial-offer': (context) => const CommercialOfferScreen(),
              '/cz-codes': (context) => const CzCodesScreen(),
              '/products': (context) => const ProductsScreen(),
              '/cz-cards': (context) => const CzCardsScreen(),
              '/cz-products': (context) => const CzProductsScreen(),
              '/cz-colors': (context) => const CzColorsScreen(),
              '/for-alice': (context) => const ForAliceScreen(),
              '/declaration': (context) => const DeclarationScreen(),
              '/far-east': (context) => const FarEastScreen(),
              '/ai-assistant': (context) => const AiAssistantScreen(),
            },
          );
        },
      ),
    );
  }
}