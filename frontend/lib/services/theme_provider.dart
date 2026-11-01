// frontend/lib/services/theme_provider.dart
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'dart:html' as html;

class ThemeProvider extends ChangeNotifier {
  static const String _storageKey = 'ved_theme_mode';

  ThemeMode _themeMode = ThemeMode.system;

  ThemeMode get themeMode => _themeMode;

  bool get isDark =>
      _themeMode == ThemeMode.dark ||
      (_themeMode == ThemeMode.system &&
          // На вебе системную тему не определить надёжно — считаем светлой
          false);

  ThemeProvider() {
    _loadFromStorage();
  }

  void _loadFromStorage() {
    if (!kIsWeb) return;
    try {
      final stored = html.window.localStorage[_storageKey];
      if (stored == 'dark') {
        _themeMode = ThemeMode.dark;
      } else if (stored == 'light') {
        _themeMode = ThemeMode.light;
      } else {
        _themeMode = ThemeMode.system;
      }
    } catch (_) {
      // ignore
    }
  }

  void _saveToStorage() {
    if (!kIsWeb) return;
    try {
      final value = switch (_themeMode) {
        ThemeMode.dark => 'dark',
        ThemeMode.light => 'light',
        ThemeMode.system => 'system',
      };
      html.window.localStorage[_storageKey] = value;
    } catch (_) {
      // ignore
    }
  }

  void setThemeMode(ThemeMode mode) {
    if (_themeMode == mode) return;
    _themeMode = mode;
    _saveToStorage();
    notifyListeners();
  }

  /// Переключает: dark <-> light. Если сейчас system — включаем dark.
  void toggleTheme() {
    if (_themeMode == ThemeMode.dark) {
      setThemeMode(ThemeMode.light);
    } else {
      setThemeMode(ThemeMode.dark);
    }
  }
}