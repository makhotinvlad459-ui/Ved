import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'home_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> with SingleTickerProviderStateMixin {
  final TextEditingController _passwordController = TextEditingController();
  bool _obscureText = true;
  bool _isLoading = false;
  String _error = '';

  // Анимация
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  static const String _correctPassword = 'ved';

  @override
  void initState() {
    super.initState();
    
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );

    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: const Interval(0.0, 1.0, curve: Curves.easeOut),
      ),
    );

    _slideAnimation = Tween<Offset>(begin: const Offset(0, 0.3), end: Offset.zero).animate(
      CurvedAnimation(
        parent: _animationController,
        curve: const Interval(0.0, 1.0, curve: Curves.easeOutCubic),
      ),
    );

    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final password = _passwordController.text.trim();

    if (password.isEmpty) {
      setState(() => _error = 'Введите пароль');
      return;
    }

    setState(() {
      _isLoading = true;
      _error = '';
    });

    await Future.delayed(const Duration(seconds: 1));

    if (password == _correctPassword) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('is_authenticated', true);

      if (mounted) {
        Navigator.pushReplacement(
          context,
          PageRouteBuilder(
            pageBuilder: (context, animation, secondaryAnimation) => const HomeScreen(),
            transitionsBuilder: (context, animation, secondaryAnimation, child) {
              return FadeTransition(
                opacity: animation,
                child: child,
              );
            },
            transitionDuration: const Duration(milliseconds: 600),
          ),
        );
      }
    } else {
      setState(() {
        _error = 'Неверный пароль';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32.0),
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: SlideTransition(
              position: _slideAnimation,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Анимированный логотип
                  TweenAnimationBuilder(
                    tween: Tween<double>(begin: 0.0, end: 1.0),
                    duration: const Duration(seconds: 2),
                    builder: (context, value, child) {
                      return Transform.scale(
                        scale: value,
                        child: Container(
                          width: 80,
                          height: 80,
                          decoration: BoxDecoration(
                            gradient: LinearGradient(
                              colors: [Colors.blue.shade700, Colors.blue.shade300],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight,
                            ),
                            borderRadius: BorderRadius.circular(20),
                            boxShadow: [
                              BoxShadow(
                                color: Colors.blue.shade200,
                                blurRadius: 20,
                                offset: const Offset(0, 10),
                              ),
                            ],
                          ),
                          child: const Center(
                            child: Text(
                              'V',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 40,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                  const SizedBox(height: 32),
                  
                  // Анимированный заголовок
                  TweenAnimationBuilder(
                    tween: Tween<double>(begin: 0.0, end: 1.0),
                    duration: const Duration(milliseconds: 800),
                    builder: (context, value, child) {
                      return Opacity(
                        opacity: value,
                        child: child,
                      );
                    },
                    child: const Column(
                      children: [
                        Text(
                          'Добро пожаловать',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        SizedBox(height: 8),
                        Text(
                          'Введите пароль для доступа',
                          style: TextStyle(
                            fontSize: 16,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 40),

                  // Поле ввода пароля
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      boxShadow: _error.isNotEmpty
                          ? [
                              BoxShadow(
                                color: Colors.red.shade200,
                                blurRadius: 8,
                              ),
                            ]
                          : null,
                    ),
                    child: TextField(
                      controller: _passwordController,
                      obscureText: _obscureText,
                      style: const TextStyle(fontSize: 16),
                      decoration: InputDecoration(
                        labelText: 'Пароль',
                        labelStyle: TextStyle(
                          color: _error.isNotEmpty ? Colors.red : Colors.grey.shade600,
                        ),
                        prefixIcon: Icon(
                          Icons.lock_outline,
                          color: _error.isNotEmpty ? Colors.red : Colors.blue.shade300,
                        ),
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: BorderSide(
                            color: _error.isNotEmpty ? Colors.red : Colors.grey.shade300,
                          ),
                        ),
                        enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: BorderSide(
                            color: _error.isNotEmpty ? Colors.red : Colors.grey.shade300,
                          ),
                        ),
                        focusedBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                          borderSide: BorderSide(
                            color: _error.isNotEmpty ? Colors.red : Colors.blue,
                            width: 2,
                          ),
                        ),
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureText ? Icons.visibility_off : Icons.visibility,
                            color: Colors.grey.shade500,
                          ),
                          onPressed: () {
                            setState(() {
                              _obscureText = !_obscureText;
                            });
                          },
                        ),
                        errorText: _error.isNotEmpty ? _error : null,
                        errorStyle: const TextStyle(
                          color: Colors.red,
                          fontSize: 13,
                        ),
                        contentPadding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      onSubmitted: (_) => _login(),
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Кнопка входа с анимацией
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 300),
                    height: 56,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(12),
                      gradient: _isLoading
                          ? null
                          : LinearGradient(
                              colors: [Colors.blue.shade700, Colors.blue.shade500],
                              begin: Alignment.centerLeft,
                              end: Alignment.centerRight,
                            ),
                      boxShadow: _isLoading
                          ? null
                          : [
                              BoxShadow(
                                color: Colors.blue.shade300,
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                    ),
                    child: ElevatedButton(
                      onPressed: _isLoading ? null : _login,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.transparent,
                        foregroundColor: Colors.white,
                        shadowColor: Colors.transparent,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: _isLoading
                          ? Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const SizedBox(
                                  height: 24,
                                  width: 24,
                                  child: CircularProgressIndicator(
                                    color: Colors.white,
                                    strokeWidth: 2,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                const Text(
                                  'Вход...',
                                  style: TextStyle(fontSize: 16),
                                ),
                              ],
                            )
                          : const Text(
                              'Войти',
                              style: TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Подсказка
                  Center(
                    child: Text(
                      'Пароль: admin123',
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade400,
                        fontStyle: FontStyle.italic,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}