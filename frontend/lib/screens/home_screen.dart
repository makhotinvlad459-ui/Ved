// frontend/lib/screens/home_screen.dart
import 'package:flutter/material.dart';
import '../widgets/world_clock_widget.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F6F8),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 40.0),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 1100),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // ============ ЛОГОТИП ============
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
                              color: Colors.blue.shade100,
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
                    ],
                  ),

                  const SizedBox(height: 40),

                  // ============ ЗАГОЛОВОК + ЧАСЫ В СТРОКУ ============
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

                      // На узких экранах часы уходят вниз, на широких — справа
                      if (!isWide) {
                        return Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            titleBlock,
                            const SizedBox(height: 16),
                            const SizedBox(
                              width: double.infinity,
                              child: WorldClockWidget(compact: true),
                            ),
                          ],
                        );
                      }

                      return Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(child: titleBlock),
                          const SizedBox(width: 24),
                          const SizedBox(
                            width: 360,
                            child: WorldClockWidget(compact: true),
                          ),
                        ],
                      );
                    },
                  ),

                  const SizedBox(height: 32),

                  // ============ ГРУППА: ОБРАБОТКА ДОКУМЕНТОВ ============
                  _GroupLabel(label: 'ОБРАБОТКА ДОКУМЕНТОВ'),
                  const SizedBox(height: 12),
                  _ResponsiveGrid(
                    items: [
                      _ServiceItem(
                        icon: Icons.description_outlined,
                        title: 'Спецификация',
                        color: Colors.blue,
                        route: '/upload',
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
                  _GroupLabel(label: 'ЧЕСТНЫЙ ЗНАК'),
                  const SizedBox(height: 12),
                  _ResponsiveGrid(
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

                  // ============ ГРУППА: СПРАВОЧНИКИ ============
                  _GroupLabel(label: 'СПРАВОЧНИКИ'),
                  const SizedBox(height: 12),
                  _ResponsiveGrid(
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
    return Row(
      children: [
        Container(
          width: 4,
          height: 16,
          decoration: BoxDecoration(
            color: Colors.blue.shade400,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.bold,
            color: Colors.grey.shade700,
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
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      elevation: 0,
      child: InkWell(
        onTap: () => Navigator.pushNamed(context, item.route),
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.grey.shade200, width: 1),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.03),
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
                      item.color.withOpacity(0.15),
                      item.color.withOpacity(0.05),
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
                color: Colors.grey.shade400,
                size: 20,
              ),
            ],
          ),
        ),
      ),
    );
  }
}