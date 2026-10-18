// frontend/lib/widgets/world_clock_widget.dart
import 'dart:async';
import 'dart:ui' show FontFeature;
import 'package:flutter/material.dart';

class WorldClockWidget extends StatefulWidget {
  final bool compact;
  const WorldClockWidget({super.key, this.compact = false});

  @override
  State<WorldClockWidget> createState() => _WorldClockWidgetState();
}

class _WorldClockWidgetState extends State<WorldClockWidget>
    with TickerProviderStateMixin {
  late Timer _timer;
  DateTime _now = DateTime.now();

  late AnimationController _fadeController;
  late Animation<double> _fadeAnimation;

  final List<_CityConfig> _cities = [
    _CityConfig(
      name: 'Москва',
      timezoneOffset: 3, // UTC+3
      gradient: [Color(0xFF0F2027), Color(0xFF203A43)],
      accent: Color(0xFF64B5F6),
    ),
    _CityConfig(
      name: 'Дубай',
      timezoneOffset: 4, // UTC+4
      gradient: [Color(0xFF4A2C00), Color(0xFF8B5A00)],
      accent: Color(0xFFFFB74D),
    ),
    _CityConfig(
      name: 'Гонконг',
      timezoneOffset: 8, // UTC+8
      gradient: [Color(0xFF2C1B47), Color(0xFF5B2C87)],
      accent: Color(0xFFCE93D8),
    ),
  ];

  @override
  void initState() {
    super.initState();

    _fadeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    )..forward();

    _fadeAnimation = CurvedAnimation(
      parent: _fadeController,
      curve: Curves.easeOut,
    );

    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _now = DateTime.now());
    });
  }

  @override
  void dispose() {
    _timer.cancel();
    _fadeController.dispose();
    super.dispose();
  }

  DateTime _cityTime(int offset) {
    final utc = _now.toUtc();
    return utc.add(Duration(hours: offset));
  }

  String _formatTime(DateTime t) {
    String two(int v) => v.toString().padLeft(2, '0');
    return '${two(t.hour)}:${two(t.minute)}:${two(t.second)}';
  }

  String _dayPart(DateTime t) {
    final h = t.hour;
    if (h >= 6 && h < 12) return '☀️ Утро';
    if (h >= 12 && h < 18) return '🌞 День';
    if (h >= 18 && h < 22) return '🌇 Вечер';
    return '🌙 Ночь';
  }

  IconData _dayIcon(DateTime t) {
    final h = t.hour;
    if (h >= 6 && h < 18) return Icons.wb_sunny;
    return Icons.nightlight_round;
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: Container(
        padding: widget.compact ? EdgeInsets.zero : const EdgeInsets.all(16),
        decoration: widget.compact
            ? null
            : BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                color: Colors.grey.shade50,
              ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            if (!widget.compact) ...[
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFF1E3C72), Color(0xFF2A5298)],
                      ),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(Icons.public,
                        color: Colors.white, size: 20),
                  ),
                  const SizedBox(width: 12),
                  const Text(
                    'Мировое время',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
            ],
            LayoutBuilder(
              builder: (context, constraints) {
                // Защита от бесконечных constraints (Row без Expanded/SizedBox)
                var width = constraints.maxWidth;
                if (!width.isFinite) {
                  width = widget.compact ? 360.0 : 600.0;
                }

                final columns = widget.compact ? 3 : (width < 600 ? 1 : 3);
                final spacing = widget.compact ? 8.0 : 12.0;
                final itemWidth = (width - spacing * (columns - 1)) / columns;

                return Wrap(
                  spacing: spacing,
                  runSpacing: spacing,
                  children: _cities.map((city) {
                    final t = _cityTime(city.timezoneOffset);
                    return SizedBox(
                      width: itemWidth,
                      child: _CityCard(
                        city: city,
                        time: t,
                        timeStr: _formatTime(t),
                        dayPart: _dayPart(t),
                        dayIcon: _dayIcon(t),
                        compact: widget.compact,
                      ),
                    );
                  }).toList(),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _CityConfig {
  final String name;
  final int timezoneOffset;
  final List<Color> gradient;
  final Color accent;

  const _CityConfig({
    required this.name,
    required this.timezoneOffset,
    required this.gradient,
    required this.accent,
  });
}

class _CityCard extends StatefulWidget {
  final _CityConfig city;
  final DateTime time;
  final String timeStr;
  final String dayPart;
  final IconData dayIcon;
  final bool compact;

  const _CityCard({
    required this.city,
    required this.time,
    required this.timeStr,
    required this.dayPart,
    required this.dayIcon,
    this.compact = false,
  });

  @override
  State<_CityCard> createState() => _CityCardState();
}

class _CityCardState extends State<_CityCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    );
    // Пульс нужен только в полном режиме — в compact не тратим кадры
    if (!widget.compact) {
      _pulseController.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 500),
      padding: widget.compact
          ? const EdgeInsets.symmetric(horizontal: 10, vertical: 10)
          : const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: widget.city.gradient,
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: widget.city.gradient.last.withOpacity(0.4),
            blurRadius: widget.compact ? 8 : 16,
            offset: const Offset(0, 6),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(widget.dayIcon,
                  color: Colors.white70, size: widget.compact ? 12 : 16),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  widget.city.name,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: widget.compact ? 11 : 14,
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              AnimatedBuilder(
                animation: _pulseController,
                builder: (context, child) {
                  final v = _pulseController.value;
                  return Container(
                    width: widget.compact ? 6 : 8,
                    height: widget.compact ? 6 : 8,
                    decoration: BoxDecoration(
                      color: Colors.green.shade400.withOpacity(0.5 + v * 0.5),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color:
                              Colors.green.shade400.withOpacity(v * 0.6),
                          blurRadius: 8 * v,
                        ),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
          SizedBox(height: widget.compact ? 6 : 12),
          Text(
            widget.timeStr,
            style: TextStyle(
              color: Colors.white,
              fontSize: widget.compact ? 16 : 26,
              fontWeight: FontWeight.bold,
              letterSpacing: widget.compact ? 0.5 : 1.5,
              fontFeatures: const [FontFeature.tabularFigures()],
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (!widget.compact) ...[
            const SizedBox(height: 4),
            Text(
              widget.dayPart,
              style: TextStyle(
                color: widget.city.accent,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }
}