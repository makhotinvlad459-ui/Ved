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
import 'screens/declaration_screen.dart';
import 'screens/far_east_screen.dart';

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
      ],
      child: MaterialApp(
        title: 'VED Processor',
        theme: ThemeData(
          primarySwatch: Colors.blue,
          useMaterial3: true,
        ),
        debugShowCheckedModeBanner: false,
        // Basic Auth на nginx уже проверил пользователя —
        // сразу открываем главный экран.
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
        },
      ),
    );
  }
}