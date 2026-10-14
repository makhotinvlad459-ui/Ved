// frontend/lib/screens/for_alice_screen.dart
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

class ForAliceScreen extends StatefulWidget {
  const ForAliceScreen({super.key});

  @override
  State<ForAliceScreen> createState() => _ForAliceScreenState();
}

class _ForAliceRow {
  final TextEditingController name;
  final TextEditingController qty;
  final TextEditingController price;

  _ForAliceRow({String name = '', String qty = '', String price = ''})
      : name = TextEditingController(text: name),
        qty = TextEditingController(text: qty),
        price = TextEditingController(text: price);

  void dispose() {
    name.dispose();
    qty.dispose();
    price.dispose();
  }
}

class _ForAliceScreenState extends State<ForAliceScreen> {
  final _rateController = TextEditingController(text: '8.3');
  final _documentsController = TextEditingController(text: '2150');
  final _usdToAedController = TextEditingController(text: '3.674');

  final List<_ForAliceRow> _rows = [_ForAliceRow()];

  bool _isProcessing = false;
  String _error = '';

  List<dynamic> _resultRows = [];
  List<dynamic> _missing = [];
  Map<String, dynamic>? _totals;

  bool _showResults = false;
  bool _hasMissing = false;
  String? _sessionId;

  @override
  void dispose() {
    _rateController.dispose();
    _documentsController.dispose();
    _usdToAedController.dispose();
    for (final r in _rows) {
      r.dispose();
    }
    super.dispose();
  }

  void _addRow() {
    setState(() {
      _rows.add(_ForAliceRow());
    });
  }

  void _removeRow(int index) {
    setState(() {
      _rows[index].dispose();
      _rows.removeAt(index);
      if (_rows.isEmpty) _rows.add(_ForAliceRow());
    });
  }

  void _clearAll() {
    setState(() {
      for (final r in _rows) {
        r.dispose();
      }
      _rows.clear();
      _rows.add(_ForAliceRow());
    });
  }

  // ============================================================
  // ВСТАВКА
  // ============================================================

  Future<void> _pasteNames() async {
    final controller = TextEditingController();
    final result = await _showPasteDialog(
      title: 'Вставить названия',
      hint: 'Скопируйте столбец с названиями из 1С и вставьте сюда (Ctrl+V)',
      controller: controller,
    );
    if (result == true) {
      final lines = _splitLines(controller.text);
      setState(() {
        for (int i = 0; i < lines.length; i++) {
          if (i < _rows.length) {
            _rows[i].name.text = lines[i];
          } else {
            _rows.add(_ForAliceRow(name: lines[i]));
          }
        }
      });
      _showSnack('Вставлено названий: ${lines.length}');
    }
  }

  Future<void> _pasteQtys() async {
    final controller = TextEditingController();
    final result = await _showPasteDialog(
      title: 'Вставить количества',
      hint: 'Скопируйте столбец с количествами из 1С и вставьте сюда (Ctrl+V)',
      controller: controller,
    );
    if (result == true) {
      final lines = _splitLines(controller.text);
      setState(() {
        for (int i = 0; i < lines.length; i++) {
          final qty = lines[i].replaceAll(RegExp(r'[^\d]'), '');
          if (i < _rows.length) {
            _rows[i].qty.text = qty;
          } else {
            _rows.add(_ForAliceRow(qty: qty));
          }
        }
      });
      _showSnack('Вставлено количеств: ${lines.length}');
    }
  }

  Future<void> _pastePrices() async {
    final controller = TextEditingController();
    final result = await _showPasteDialog(
      title: 'Вставить цены',
      hint: 'Скопируйте столбец с ценами из 1С и вставьте сюда (Ctrl+V)',
      controller: controller,
    );
    if (result == true) {
      final lines = _splitLines(controller.text);
      setState(() {
        for (int i = 0; i < lines.length; i++) {
          final price = lines[i]
              .replaceAll(',', '.')
              .replaceAll(RegExp(r'[^\d.]'), '');
          if (i < _rows.length) {
            _rows[i].price.text = price;
          } else {
            _rows.add(_ForAliceRow(price: price));
          }
        }
      });
      _showSnack('Вставлено цен: ${lines.length}');
    }
  }

  // ============================================================
  // ВСПОМОГАТЕЛЬНЫЕ
  // ============================================================

  List<String> _splitLines(String text) {
    return text
        .replaceAll('\r\n', '\n')
        .replaceAll('\r', '\n')
        .split('\n')
        .map((l) => l.trim())
        .where((l) => l.isNotEmpty)
        .toList();
  }

  Future<bool?> _showPasteDialog({
    required String title,
    required String hint,
    required TextEditingController controller,
  }) {
    return showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: SizedBox(
          width: 600,
          height: 400,
          child: TextField(
            controller: controller,
            maxLines: null,
            expands: true,
            textAlignVertical: TextAlignVertical.top,
            decoration: InputDecoration(
              hintText: hint,
              border: const OutlineInputBorder(),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Отмена'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.teal,
              foregroundColor: Colors.white,
            ),
            child: const Text('Вставить'),
          ),
        ],
      ),
    );
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.green),
    );
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
  }

  List<Map<String, dynamic>> _collectItems() {
    final items = <Map<String, dynamic>>[];
    for (final r in _rows) {
      final name = r.name.text.trim();
      final qtyText = r.qty.text.trim();
      final priceText = r.price.text.trim();

      if (name.isEmpty && qtyText.isEmpty && priceText.isEmpty) continue;
      if (name.isEmpty) continue;

      items.add({
        'name': name,
        'qty': int.tryParse(qtyText) ?? 0,
        'price': double.tryParse(priceText.replaceAll(',', '.')) ?? 0.0,
      });
    }
    return items;
  }

  Future<void> _process() async {
    final items = _collectItems();
    if (items.isEmpty) {
      _showError('Добавьте хотя бы одну позицию');
      return;
    }

    final rate = double.tryParse(_rateController.text.replaceAll(',', '.'));
    final documents =
        double.tryParse(_documentsController.text.replaceAll(',', '.'));
    final usdToAed =
        double.tryParse(_usdToAedController.text.replaceAll(',', '.'));

    if (rate == null || documents == null || usdToAed == null) {
      _showError('Проверьте параметры расчёта');
      return;
    }

    setState(() {
      _isProcessing = true;
      _error = '';
    });

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.forAliceGenerate(
        items: items,
        logisticsRateUsd: rate,
        usdToAed: usdToAed,
        documentsCostAed: documents,
      );

      if (!mounted) return;

      setState(() {
        _isProcessing = false;
        _resultRows = result['rows'] ?? [];
        _missing = result['missing'] ?? [];
        _totals = result['totals'] ?? {};
        _showResults = true;
        _hasMissing = _missing.isNotEmpty;
        _sessionId = result['session_id'];
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isProcessing = false;
        _error = '$e';
      });
    }
  }

  Future<void> _saveWeightAndRecalculate(int index) async {
    final m = _missing[index];
    final partNumber = m['part_number'];
    final name = m['name'] ?? '';

    if (partNumber == null) {
      _showError('Не удалось извлечь part_number из названия');
      return;
    }

    final controller = TextEditingController();
    final weight = await showDialog<double>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Вес для $partNumber'),
        content: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(
            labelText: 'Вес (кг)',
            hintText: '3.9',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
          ElevatedButton(
            onPressed: () {
              final v = double.tryParse(controller.text.replaceAll(',', '.'));
              if (v != null && v > 0) {
                Navigator.pop(context, v);
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.teal,
              foregroundColor: Colors.white,
            ),
            child: const Text('Сохранить'),
          ),
        ],
      ),
    );

    if (weight == null) return;

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final res = await api.forAliceSaveWeight(
        partNumber: partNumber,
        name: name,
        weight: weight,
      );

      if (!mounted) return;
      final created = res['created'] == true;
      _showSnack(created
          ? '✅ Товар создан. Пересчитываем...'
          : '✅ Вес обновлён. Пересчитываем...');

      await _process();
    } catch (e) {
      if (!mounted) return;
      _showError('❌ Ошибка: $e');
    }
  }

  Future<void> _download() async {
    if (_sessionId == null) return;
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final response = await api.forAliceDownload(_sessionId!);
      final bytes = response.data as List<int>;
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download',
            'For_Alice_${_sessionId!.substring(0, 8)}.xlsx')
        ..click();
      html.Url.revokeObjectUrl(url);
    } catch (e) {
      if (!mounted) return;
      _showError('❌ Ошибка скачивания: $e');
    }
  }

  void _reset() {
    setState(() {
      _showResults = false;
      _resultRows = [];
      _missing = [];
      _totals = null;
      _hasMissing = false;
      _sessionId = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('For Alice'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          if (_showResults)
            IconButton(
              icon: const Icon(Icons.refresh),
              tooltip: 'Новый расчёт',
              onPressed: _reset,
            ),
        ],
      ),
      body: _showResults ? _buildResults() : _buildInput(),
    );
  }

  // ============================================================
  // ЭКРАН ВВОДА
  // ============================================================

  Widget _buildInput() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            'Параметры расчёта',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _rateController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Ставка логистики (USD/кг)',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: TextField(
                  controller: _usdToAedController,
                  keyboardType:
                      const TextInputType.numberWithOptions(decimal: true),
                  decoration: const InputDecoration(
                    labelText: 'Курс USD → AED',
                    border: OutlineInputBorder(),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _documentsController,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: const InputDecoration(
              labelText: 'Расходы на документы (AED)',
              border: OutlineInputBorder(),
            ),
          ),

          const SizedBox(height: 24),

          const Text(
            'Позиции',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            'Вставьте 3 столбца из 1С — названия, количества, цены:',
            style: TextStyle(fontSize: 13, color: Colors.grey),
          ),
          const SizedBox(height: 12),

          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              ElevatedButton.icon(
                onPressed: _pasteNames,
                icon: const Icon(Icons.description_outlined, size: 18),
                label: const Text('Вставить названия'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                ),
              ),
              ElevatedButton.icon(
                onPressed: _pasteQtys,
                icon: const Icon(Icons.numbers, size: 18),
                label: const Text('Вставить количества'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                ),
              ),
              ElevatedButton.icon(
                onPressed: _pastePrices,
                icon: const Icon(Icons.attach_money, size: 18),
                label: const Text('Вставить цены'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purple,
                  foregroundColor: Colors.white,
                ),
              ),
            ],
          ),

          const SizedBox(height: 16),

          Row(
            children: [
              OutlinedButton.icon(
                onPressed: _addRow,
                icon: const Icon(Icons.add, size: 18),
                label: const Text('Добавить строку'),
              ),
              const SizedBox(width: 8),
              TextButton.icon(
                onPressed: _clearAll,
                icon: const Icon(Icons.clear_all, size: 18),
                label: const Text('Очистить всё'),
                style: TextButton.styleFrom(foregroundColor: Colors.red),
              ),
            ],
          ),

          const SizedBox(height: 12),

          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
            child: Row(
              children: const [
                SizedBox(width: 30, child: Text('#', style: TextStyle(fontSize: 12, color: Colors.grey))),
                SizedBox(width: 6),
                Expanded(flex: 5, child: Text('Название', style: TextStyle(fontSize: 12, color: Colors.grey))),
                SizedBox(width: 6),
                SizedBox(width: 70, child: Text('Кол-во', style: TextStyle(fontSize: 12, color: Colors.grey))),
                SizedBox(width: 6),
                SizedBox(width: 90, child: Text('Цена', style: TextStyle(fontSize: 12, color: Colors.grey))),
                SizedBox(width: 36),
              ],
            ),
          ),

          ...List.generate(_rows.length, (idx) {
            final r = _rows[idx];
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SizedBox(
                    width: 30,
                    child: Padding(
                      padding: const EdgeInsets.only(top: 12),
                      child: Text('${idx + 1}',
                          style: const TextStyle(fontSize: 12, color: Colors.grey)),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    flex: 5,
                    child: TextField(
                      controller: r.name,
                      maxLines: 2,
                      minLines: 1,
                      decoration: const InputDecoration(
                        isDense: true,
                        border: OutlineInputBorder(),
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 8, vertical: 10),
                      ),
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                  const SizedBox(width: 6),
                  SizedBox(
                    width: 70,
                    child: TextField(
                      controller: r.qty,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        isDense: true,
                        border: OutlineInputBorder(),
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 8, vertical: 10),
                      ),
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                  const SizedBox(width: 6),
                  SizedBox(
                    width: 90,
                    child: TextField(
                      controller: r.price,
                      keyboardType: const TextInputType.numberWithOptions(
                          decimal: true),
                      decoration: const InputDecoration(
                        isDense: true,
                        border: OutlineInputBorder(),
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 8, vertical: 10),
                      ),
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline,
                        color: Colors.red, size: 20),
                    onPressed: () => _removeRow(idx),
                    tooltip: 'Удалить',
                  ),
                ],
              ),
            );
          }),

          const SizedBox(height: 24),

          if (_error.isNotEmpty) ...[
            Text(_error, style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 12),
          ],

          ElevatedButton(
            onPressed: _isProcessing ? null : _process,
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.teal,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isProcessing
                ? const SizedBox(
                    height: 24,
                    width: 24,
                    child: CircularProgressIndicator(
                      color: Colors.white,
                      strokeWidth: 2,
                    ),
                  )
                : const Text(
                    'Рассчитать',
                    style: TextStyle(fontSize: 16),
                  ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // ЭКРАН РЕЗУЛЬТАТОВ
  // ============================================================

  Widget _buildResults() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_hasMissing) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.orange.shade50,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.orange.shade300),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.warning_amber,
                          color: Colors.orange.shade700),
                      const SizedBox(width: 8),
                      Text(
                        'Не найдены веса: ${_missing.length}',
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: Colors.orange.shade900,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Введите вес — товар создастся автоматически и пересчитается',
                    style: TextStyle(fontSize: 12, color: Colors.black87),
                  ),
                  const SizedBox(height: 12),
                  ...List.generate(_missing.length, (idx) {
                    final m = _missing[idx];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              m['part_number'] ?? '—',
                              style:
                                  const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              m['name'] ?? '',
                              style: TextStyle(
                                  fontSize: 12, color: Colors.grey[700]),
                            ),
                            const SizedBox(height: 8),
                            Align(
                              alignment: Alignment.centerRight,
                              child: ElevatedButton.icon(
                                onPressed: () => _saveWeightAndRecalculate(idx),
                                icon: const Icon(Icons.add_circle_outline,
                                    size: 18),
                                label: const Text('Ввести вес'),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.orange,
                                  foregroundColor: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],

          if (!_hasMissing && _totals != null) ...[
            Card(
              color: Colors.teal.shade50,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Итоги',
                      style:
                          TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                        'Общий вес: ${(_totals!['total_weight'] as num).toStringAsFixed(2)} кг'),
                    Text(
                        'Ставка AED/кг: ${(_totals!['rate_aed_per_kg'] as num).toStringAsFixed(2)}'),
                    Text(
                        'Итого сумма: ${(_totals!['total_sum'] as num).toStringAsFixed(2)} AED'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
          ],

          if (_resultRows.isNotEmpty) ...[
            const Text(
              'Результаты',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: DataTable(
                columnSpacing: 16,
                headingRowHeight: 40,
                dataRowHeight: 56,
                columns: const [
                  DataColumn(label: Text('P/N')),
                  DataColumn(label: Text('Название')),
                  DataColumn(label: Text('Кол')),
                  DataColumn(label: Text('Вес+15%')),
                  DataColumn(label: Text('Общий вес')),
                  DataColumn(label: Text('Цена')),
                  DataColumn(label: Text('Лог/ед')),
                  DataColumn(label: Text('Ц+лог')),
                  DataColumn(label: Text('Итог/ед')),
                  DataColumn(label: Text('Итого')),
                ],
                rows: _resultRows.map((r) {
                  return DataRow(cells: [
                    DataCell(Text(r['part_number'] ?? '—')),
                    DataCell(SizedBox(
                      width: 200,
                      child: Text(
                        r['name'] ?? '',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 12),
                      ),
                    )),
                    DataCell(Text('${r['qty'] ?? 0}')),
                    DataCell(Text(_num(r['g']))),
                    DataCell(Text(_num(r['h']))),
                    DataCell(Text(_num(r['price']))),
                    DataCell(Text(_num(r['l']))),
                    DataCell(Text(_num(r['m']))),
                    DataCell(Text(_num(r['o']))),
                    DataCell(Text(_num(r['p']))),
                  ]);
                }).toList(),
              ),
            ),
          ],

          const SizedBox(height: 24),

          if (!_hasMissing && _sessionId != null)
            ElevatedButton.icon(
              onPressed: _download,
              icon: const Icon(Icons.download),
              label:
                  const Text('Скачать xlsx', style: TextStyle(fontSize: 16)),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.teal,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),

          const SizedBox(height: 12),
          TextButton.icon(
            onPressed: _reset,
            icon: const Icon(Icons.arrow_back),
            label: const Text('Назад к вводу'),
          ),
        ],
      ),
    );
  }

  String _num(dynamic v) {
    if (v == null) return '—';
    if (v is num) return v.toStringAsFixed(2);
    return v.toString();
  }
}