// frontend/lib/screens/home_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_3d_controller/flutter_3d_controller.dart';

import '../services/theme_provider.dart';
import '../widgets/world_clock_widget.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      // Фон берется из темы (в светлой - #F5F6F8, в темной - #121212)
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 15.0, vertical: 40.0),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1300),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ============ ЛОГОТИП + ПЕРЕКЛЮЧАТЕЛЬ ТЕМЫ ============
                  Row(
                    children: [
                      Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [Colors.blue.shade700, Colors.blue.shade400],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          borderRadius: BorderRadius.circular(12),
                          boxShadow: [
                            BoxShadow(
                              color: Colors.blue.shade100
                                  .withOpacity(isDark ? 0.1 : 1.0),
                              blurRadius: 12,
                              offset: const Offset(0, 4),
                            ),
                          ],
                        ),
                        child: const Center(
                          child: Text(
                            'V',
                            style: TextStyle(
                              color: Colors.white,
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Text(
                        'VED Processor',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const Spacer(),
                      // === ПЕРЕКЛЮЧАТЕЛЬ ТЕМЫ ===
                      Consumer<ThemeProvider>(
                        builder: (context, themeProvider, _) {
                          final isDarkMode =
                              Theme.of(context).brightness == Brightness.dark;
                          return IconButton(
                            tooltip:
                                isDarkMode ? 'Светлая тема' : 'Тёмная тема',
                            icon: Icon(
                              isDarkMode
                                  ? Icons.light_mode_outlined
                                  : Icons.dark_mode_outlined,
                              color: isDarkMode
                                  ? Colors.amber.shade400
                                  : Colors.blueGrey,
                            ),
                            onPressed: themeProvider.toggleTheme,
                          );
                        },
                      ),
                    ],
                  ),

                  const SizedBox(height: 40),

                  // ============ ЗАГОЛОВОК + ЧАСЫ + 3D ============
                  LayoutBuilder(
                    builder: (context, constraints) {
                      final isWide = constraints.maxWidth >= 800;

                      final titleBlock = Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: const [
                          Text(
                            'Выберите сервис',
                            style: TextStyle(
                              fontSize: 28,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Обработка документов и управление справочниками',
                            style: TextStyle(
                              fontSize: 15,
                              color: Colors.grey,
                            ),
                          ),
                        ],
                      );

                      final clockBlock = const SizedBox(
                        width: 360,
                        child: WorldClockWidget(compact: true),
                      );

                      // Новый блок с 3D-моделью
                      final iphoneBlock = const SizedBox(
                        height: 350,
                        width: double.infinity,
                        child: Iphone3DViewer(),
                      );

                      if (!isWide) {
                        // На мобильных/узких экранах: Заголовок -> 3D -> Часы
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            titleBlock,
                            const SizedBox(height: 24),
                            iphoneBlock,
                            const SizedBox(height: 24),
                            const SizedBox(
                              width: double.infinity,
                              child: WorldClockWidget(compact: true),
                            ),
                          ],
                        );
                      }

                      // На широких экранах: Слева Заголовок + 3D, Справа Часы
                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                titleBlock,
                                const SizedBox(height: 24),
                                iphoneBlock,
                              ],
                            ),
                          ),
                          const SizedBox(width: 24),
                          clockBlock,
                        ],
                      );
                    },
                  ),

                  const SizedBox(height: 32),

                  // ============ ГРУППА: ОБРАБОТКА ДОКУМЕНТОВ ============
                  const _GroupLabel(label: 'ОБРАБОТКА ДОКУМЕНТОВ'),
                  const SizedBox(height: 12),
                  const _ResponsiveGrid(
                    items: [
                      _ServiceItem(
                        icon: Icons.description_outlined,
                        title: 'Спецификация',
                        color: Colors.blue,
                        route: '/upload',
                      ),
                      _ServiceItem(
                        icon: Icons.gavel_outlined,
                        title: 'Декларирование',
                        color: Colors.brown,
                        route: '/declaration',
                      ),
                      _ServiceItem(
                        icon: Icons.local_shipping_outlined,
                        title: 'Far East',
                        color: Colors.indigo,
                        route: '/far-east',
                      ),
                      _ServiceItem(
                        icon: Icons.inventory_2_outlined,
                        title: 'Packing List',
                        color: Colors.orange,
                        route: '/packing-list',
                      ),
                      _ServiceItem(
                        icon: Icons.request_quote_outlined,
                        title: 'КП',
                        color: Colors.teal,
                        route: '/commercial-offer',
                      ),
                      _ServiceItem(
                        icon: Icons.calculate_outlined,
                        title: 'For Alice',
                        color: Colors.green,
                        route: '/for-alice',
                      ),
                    ],
                  ),

                  const SizedBox(height: 32),

                  // ============ ГРУППА: ЧЕСТНЫЙ ЗНАК ============
                  const _GroupLabel(label: 'ЧЕСТНЫЙ ЗНАК'),
                  const SizedBox(height: 12),
                  const _ResponsiveGrid(
                    items: [
                      _ServiceItem(
                        icon: Icons.qr_code_2,
                        title: 'ЧЗ в спецификацию',
                        color: Colors.purple,
                        route: '/cz-upload',
                      ),
                      _ServiceItem(
                        icon: Icons.qr_code_scanner,
                        title: 'ЧЗ по странам',
                        color: Colors.indigo,
                        route: '/cz-codes',
                      ),
                      _ServiceItem(
                        icon: Icons.credit_card_outlined,
                        title: 'Карточки ЧЗ',
                        color: Colors.deepPurple,
                        route: '/cz-cards',
                      ),
                    ],
                  ),

                  const SizedBox(height: 32),

                  // ============ ГРУППА: ИИ-АССИСТЕНТ ============
                  const _GroupLabel(label: 'ИИ-АССИСТЕНТ'),
                  const SizedBox(height: 12),
                  const _ResponsiveGrid(
                    items: [
                      _ServiceItem(
                        icon: Icons.auto_awesome,
                        title: 'AI-ассистент',
                        color: Colors.deepPurple,
                        route: '/ai-assistant',
                      ),
                    ],
                  ),

                  const SizedBox(height: 32),

                  // ============ ГРУППА: СПРАВОЧНИКИ ============
                  const _GroupLabel(label: 'СПРАВОЧНИКИ'),
                  const SizedBox(height: 12),
                  const _ResponsiveGrid(
                    items: [
                      _ServiceItem(
                        icon: Icons.inventory_outlined,
                        title: 'Товары',
                        color: Colors.blueGrey,
                        route: '/products',
                      ),
                      _ServiceItem(
                        icon: Icons.phone_iphone,
                        title: 'Модели ЧЗ',
                        color: Colors.deepPurple,
                        route: '/cz-products',
                      ),
                      _ServiceItem(
                        icon: Icons.palette_outlined,
                        title: 'Цвета ЧЗ',
                        color: Colors.deepPurple,
                        route: '/cz-colors',
                      ),
                    ],
                  ),

                  const SizedBox(height: 40),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _ServiceItem {
  final IconData icon;
  final String title;
  final Color color;
  final String route;

  const _ServiceItem({
    required this.icon,
    required this.title,
    required this.color,
    required this.route,
  });
}

class _GroupLabel extends StatelessWidget {
  final String label;

  const _GroupLabel({required this.label});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Row(
      children: [
        Container(
          width: 4,
          height: 16,
          decoration: BoxDecoration(
            color: isDark ? Colors.blue.shade300 : Colors.blue.shade400,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: isDark ? Colors.grey.shade400 : Colors.grey.shade700,
            letterSpacing: 1.2,
          ),
        ),
      ],
    );
  }
}

class _ResponsiveGrid extends StatelessWidget {
  final List<_ServiceItem> items;

  const _ResponsiveGrid({required this.items});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final width = constraints.maxWidth;
        int columns;
        if (width < 500) {
          columns = 1;
        } else if (width < 900) {
          columns = 2;
        } else {
          columns = 3;
        }

        final effectiveColumns =
            items.length < columns ? items.length : columns;

        const spacing = 12.0;
        final itemWidth =
            (width - spacing * (effectiveColumns - 1)) / effectiveColumns;

        return Wrap(
          spacing: spacing,
          runSpacing: spacing,
          children: items.map((item) {
            return SizedBox(
              width: itemWidth,
              child: _CompactCard(item: item),
            );
          }).toList(),
        );
      },
    );
  }
}

class _CompactCard extends StatelessWidget {
  final _ServiceItem item;

  const _CompactCard({required this.item});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Material(
      // Фон карточки берется из темы (в темной - #1E1E1E)
      color: Theme.of(context).cardColor,
      borderRadius: BorderRadius.circular(14),
      elevation: 0,
      child: InkWell(
        onTap: () => Navigator.pushNamed(context, item.route),
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: isDark ? Colors.grey.shade800 : Colors.grey.shade200,
              width: 1,
            ),
            boxShadow: [
              BoxShadow(
                color: isDark
                    ? Colors.black.withOpacity(0.2)
                    : Colors.black.withOpacity(0.03),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    colors: [
                      item.color.withOpacity(isDark ? 0.25 : 0.15),
                      item.color.withOpacity(isDark ? 0.1 : 0.05),
                    ],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: Icon(item.icon, color: item.color, size: 24),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  item.title,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              Icon(
                Icons.chevron_right,
                color: isDark ? Colors.grey.shade600 : Colors.grey.shade400,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================
// 3D МОДЕЛЬ 
// ============================================================
class Iphone3DViewer extends StatefulWidget {
  const Iphone3DViewer({super.key});

  @override
  State<Iphone3DViewer> createState() => _Iphone3DViewerState();
}

class _Iphone3DViewerState extends State<Iphone3DViewer> {
  final Flutter3DController _controller = Flutter3DController();



  @override
  Widget build(BuildContext context) {
    // Получаем цвет фона страницы (светло-серый или темный)
    final bgColor = Theme.of(context).scaffoldBackgroundColor;

    return Container(
      // Убрали явный white background
      child: ClipRRect(
        borderRadius: BorderRadius.circular(24),
        child: ColorFiltered(
          // Этот фильтр делает белый цвет (255, 255, 255) прозрачным
          colorFilter: const ColorFilter.mode(
            Colors.white, 
            BlendMode.dstOut,
          ),
          child: Flutter3DViewer(
            controller: _controller,
            src: 'assets/assets/models/mastertux-compass-1679.glb',
            onLoad: (modelAddress) {
              _controller.startRotation(rotationSpeed: 15);
            },
            enableTouch: true, 
            activeGestureInterceptor: true,
        ),
      ),
    );
  }
}