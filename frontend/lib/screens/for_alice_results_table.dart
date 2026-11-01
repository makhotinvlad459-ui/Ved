import 'package:flutter/material.dart';

class ForAliceResultsTable extends StatelessWidget {
  final List<dynamic> rows;
  final void Function(int oldIndex, int newIndex) onReorder;

  const ForAliceResultsTable({
    super.key,
    required this.rows,
    required this.onReorder,
  });

  String _num(dynamic v) {
    if (v == null) return '—';
    if (v is num) return v.toStringAsFixed(2);
    return v.toString();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isDark = theme.brightness == Brightness.dark;

    // Адаптивные цвета под тему
    final headerBg = isDark
        ? theme.colorScheme.surfaceContainerHighest // тёмный нейтральный фон
        : Colors.grey.shade200;
    final headerTextColor = isDark
        ? theme.colorScheme.onSurface
        : Colors.black87;
    final dragHandleColor =
        isDark ? Colors.grey.shade500 : Colors.grey;

    return SelectionArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // === ФИКСИРОВАННЫЙ ЗАГОЛОВОК ===
          Container(
            color: headerBg,
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
            child: Row(
              children: [
                SizedBox(
                  width: 30,
                  child: Icon(Icons.drag_handle,
                      size: 18, color: dragHandleColor),
                ),
                _HeaderCell('Модель', flex: 15, color: headerTextColor),
                _HeaderCell('P/N', flex: 15, color: headerTextColor),
                _HeaderCell('Наименование', flex: 40, color: headerTextColor),
                _HeaderCell('Кол', flex: 6, color: headerTextColor, center: true),
                _HeaderCell('Вес', flex: 8, color: headerTextColor, center: true),
                _HeaderCell('+15%', flex: 8, color: headerTextColor, center: true),
                _HeaderCell('Общий', flex: 8, color: headerTextColor, center: true),
                _HeaderCell('Цена', flex: 10, color: headerTextColor, center: true),
                _HeaderCell('Ст-ть', flex: 10, color: headerTextColor, center: true),
                _HeaderCell('Лог', flex: 8, color: headerTextColor, center: true),
                _HeaderCell('Ц+лог', flex: 8, color: headerTextColor, center: true),
                _HeaderCell('С лог', flex: 10, color: headerTextColor, center: true),
                _HeaderCell('+ЧЗ', flex: 6, color: headerTextColor, center: true),
                _HeaderCell('Итог/ед', flex: 8, color: headerTextColor, center: true),
                _HeaderCell('Итого', flex: 10, color: headerTextColor, center: true),
              ],
            ),
          ),

          // === СПИСОК С ПЕРЕТАСКИВАНИЕМ ===
          Expanded(
            child: ReorderableListView.builder(
              itemCount: rows.length,
              onReorder: onReorder,
              buildDefaultDragHandles: false,
              itemBuilder: (context, index) {
                final r = rows[index];
                final qty = (r['qty'] as num?)?.toDouble() ?? 0;
                final price = (r['price'] as num?)?.toDouble() ?? 0;
                final m = (r['m'] as num?)?.toDouble() ?? 0;
                final isCz = r['is_cz'] == true;

                return Card(
                  key: ValueKey(r['part_number'] ?? index),
                  margin: const EdgeInsets.symmetric(vertical: 1, horizontal: 0),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 4.0),
                    child: Row(
                      children: [
                        ReorderableDragStartListener(
                          index: index,
                          child: SizedBox(
                            width: 30,
                            child: Icon(Icons.drag_handle,
                                size: 16, color: dragHandleColor),
                          ),
                        ),
                        _Cell(r['model_number'] ?? '—', flex: 15),
                        _Cell(r['part_number'] ?? '—', flex: 15),
                        _Cell(r['name'] ?? '', flex: 40),
                        _Cell('${r['qty'] ?? 0}', flex: 6, center: true),
                        _Cell(_num(r['weight']), flex: 8, center: true),
                        _Cell(_num(r['g']), flex: 8, center: true),
                        _Cell(_num(r['h']), flex: 8, center: true),
                        _Cell(_num(r['price']), flex: 10, center: true),
                        _Cell(_num(price * qty), flex: 10, center: true),
                        _Cell(_num(r['l']), flex: 8, center: true),
                        _Cell(_num(r['m']), flex: 8, center: true),
                        _Cell(_num(m * qty), flex: 10, center: true),
                        Expanded(
                          flex: 6,
                          child: Text(
                            isCz ? '+1.5' : '—',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 11,
                              color: isCz
                                  ? (isDark
                                      ? Colors.green.shade300
                                      : Colors.green.shade700)
                                  : theme.colorScheme.onSurfaceVariant,
                              fontWeight:
                                  isCz ? FontWeight.bold : FontWeight.normal,
                            ),
                          ),
                        ),
                        _Cell(_num(r['o']), flex: 8, center: true),
                        Expanded(
                          flex: 10,
                          child: Text(
                            _num(r['p']),
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: theme.colorScheme.onSurface,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

/// Ячейка заголовка
class _HeaderCell extends StatelessWidget {
  final String text;
  final int flex;
  final Color color;
  final bool center;

  const _HeaderCell(this.text,
      {required this.flex, required this.color, this.center = false});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      flex: flex,
      child: Text(
        text,
        textAlign: center ? TextAlign.center : TextAlign.start,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.bold,
          color: color,
        ),
        overflow: TextOverflow.ellipsis,
      ),
    );
  }
}

/// Обычная ячейка строки
class _Cell extends StatelessWidget {
  final String text;
  final int flex;
  final bool center;

  const _Cell(this.text, {required this.flex, this.center = false});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      flex: flex,
      child: Text(
        text,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        textAlign: center ? TextAlign.center : TextAlign.start,
        style: const TextStyle(fontSize: 11),
      ),
    );
  }
}