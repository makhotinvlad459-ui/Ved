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
    return SelectionArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // === ФИКСИРОВАННЫЙ ЗАГОЛОВОК ===
          Container(
            color: Colors.grey.shade200,
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
            child: const Row(
              children: [
                SizedBox(width: 30, child: Icon(Icons.drag_handle, size: 18, color: Colors.grey)),
                Expanded(flex: 15, child: Text('Модель', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 15, child: Text('P/N', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 40, child: Text('Наименование', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 6, child: Text('Кол', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 8, child: Text('Вес', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 8, child: Text('+15%', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 8, child: Text('Общий', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 10, child: Text('Цена', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 10, child: Text('Ст-ть', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 8, child: Text('Лог', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 8, child: Text('Ц+лог', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 10, child: Text('С лог', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 6, child: Text('+ЧЗ', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 8, child: Text('Итог/ед', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
                Expanded(flex: 10, child: Text('Итого', textAlign: TextAlign.center, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold))),
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
                          child: const SizedBox(
                            width: 30,
                            child: Icon(Icons.drag_handle, size: 16, color: Colors.grey),
                          ),
                        ),
                        Expanded(flex: 15, child: Text(r['model_number'] ?? '—', style: const TextStyle(fontSize: 11), overflow: TextOverflow.ellipsis)),
                        Expanded(flex: 15, child: Text(r['part_number'] ?? '—', style: const TextStyle(fontSize: 11), overflow: TextOverflow.ellipsis)),
                        Expanded(flex: 40, child: Text(r['name'] ?? '', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 6, child: Text('${r['qty'] ?? 0}', textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 8, child: Text(_num(r['weight']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 8, child: Text(_num(r['g']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 8, child: Text(_num(r['h']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 10, child: Text(_num(r['price']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 10, child: Text(_num(price * qty), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 8, child: Text(_num(r['l']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 8, child: Text(_num(r['m']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 10, child: Text(_num(m * qty), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(
                          flex: 6, 
                          child: Text(
                            isCz ? '+1.5' : '—',
                            textAlign: TextAlign.center, 
                            style: TextStyle(
                              fontSize: 11, 
                              color: isCz ? Colors.green.shade700 : Colors.grey,
                              fontWeight: isCz ? FontWeight.bold : FontWeight.normal,
                            )
                          )
                        ),
                        Expanded(flex: 8, child: Text(_num(r['o']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11))),
                        Expanded(flex: 10, child: Text(_num(r['p']), textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold))),
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