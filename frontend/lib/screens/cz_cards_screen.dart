// frontend/lib/screens/cz_cards_screen.dart
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

class CzCardsScreen extends StatefulWidget {
  const CzCardsScreen({super.key});

  @override
  State<CzCardsScreen> createState() => _CzCardsScreenState();
}

class _CzCardsScreenState extends State<CzCardsScreen> {
  FilePickerResult? _invoiceResult;
  bool _isLoading = false;
  String _sessionId = '';

  final Set<String> _selectedParts = {};
  List<dynamic> _items = [];
  bool _showItems = false;

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx'],
      );
      if (result != null && result.files.single.bytes != null) {
        setState(() {
          _invoiceResult = result;
          _showItems = false;
          _items = [];
          _selectedParts.clear();
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка: $e')),
        );
      }
    }
  }

  Future<void> _parseInvoice() async {
    if (_invoiceResult == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Выберите инвойс'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final bytes = _invoiceResult!.files.single.bytes;
    if (bytes == null) return;

    setState(() => _isLoading = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.parseCzInvoice(
        bytes: bytes,
        fileName: _invoiceResult!.files.single.name,
      );

      if (!mounted) return;
      setState(() {
        _sessionId = result['session_id'];
        _items = result['items'] ?? [];
        _showItems = true;
        _isLoading = false;
        // По умолчанию все выбраны
        _selectedParts.addAll(
          _items.map((it) => it['part_number'] as String).toSet().cast<String>(),
        );
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Распознано ${_items.length} позиций'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _generate() async {
    if (_selectedParts.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Выберите хотя бы одну позицию'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.generateCzCards(
        sessionId: _sessionId,
        partNumbers: _selectedParts.toList(),
      );

      if (!mounted) return;
      setState(() => _isLoading = false);

      final files = result['files'] as Map<String, dynamic>? ?? {};

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => CzCardsResultScreen(
            sessionId: _sessionId,
            files: files,
          ),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  void _toggleAll(bool value) {
    setState(() {
      if (value) {
        _selectedParts.addAll(
          _items.map((it) => it['part_number'] as String).toSet().cast<String>(),
        );
      } else {
        _selectedParts.clear();
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Карточки ЧЗ'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _showItems ? _buildItemsList() : _buildUploadView(),
      ),
    );
  }

  Widget _buildUploadView() {
    final fileName = _invoiceResult?.files.single.name;
    final hasFile = fileName != null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Container(
              width: 56,
              height: 56,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.purple.shade600, Colors.purple.shade300],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(16),
              ),
              child: const Icon(Icons.credit_card_outlined, color: Colors.white, size: 30),
            ),
            const SizedBox(width: 16),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Создание карточек ЧЗ',
                    style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                  ),
                  SizedBox(height: 4),
                  Text(
                    'Инвойс → выбор позиций → K3-файлы',
                    style: TextStyle(color: Colors.grey, fontSize: 14),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 32),

        GestureDetector(
          onTap: _pickFile,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: hasFile ? Colors.purple.shade50 : Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: hasFile ? Colors.purple : Colors.grey.shade300,
                width: hasFile ? 2 : 1,
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 52,
                  height: 52,
                  decoration: BoxDecoration(
                    color: hasFile ? Colors.purple.withOpacity(0.15) : Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(
                    hasFile ? Icons.check_circle : Icons.upload_file,
                    color: hasFile ? Colors.purple : Colors.grey.shade500,
                    size: 28,
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Инвойс (.xlsx)',
                        style: TextStyle(fontSize: 13, color: Colors.grey),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        fileName ?? 'Нажмите для выбора файла',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w500,
                          color: hasFile ? Colors.black : Colors.grey,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),

        ElevatedButton(
          onPressed: _isLoading ? null : _parseInvoice,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.purple,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: _isLoading
              ? const SizedBox(
                  height: 24,
                  width: 24,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                )
              : const Text('Распознать инвойс', style: TextStyle(fontSize: 16)),
        ),
      ],
    );
  }

  Widget _buildItemsList() {
    final allSelected = _selectedParts.length == _items.length && _items.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Найдено позиций: ${_items.length}',
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
            ),
            Text(
              'Выбрано: ${_selectedParts.length}',
              style: TextStyle(fontSize: 14, color: Colors.purple.shade700),
            ),
          ],
        ),
        const SizedBox(height: 12),

        Row(
          children: [
            Checkbox(
              value: allSelected,
              onChanged: (v) => _toggleAll(v ?? false),
            ),
            const Text('Выбрать все'),
            const Spacer(),
            TextButton.icon(
              onPressed: () {
                setState(() {
                  _showItems = false;
                  _items = [];
                  _selectedParts.clear();
                  _invoiceResult = null;
                });
              },
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Другой инвойс'),
            ),
          ],
        ),
        const SizedBox(height: 8),

        Expanded(
          child: ListView.builder(
            itemCount: _items.length,
            itemBuilder: (context, index) {
              final it = _items[index];
              final partNumber = it['part_number'] as String;
              final isSelected = _selectedParts.contains(partNumber);

              return Card(
                margin: const EdgeInsets.only(bottom: 8),
                child: CheckboxListTile(
                  value: isSelected,
                  onChanged: (v) {
                    setState(() {
                      if (v == true) {
                        _selectedParts.add(partNumber);
                      } else {
                        _selectedParts.remove(partNumber);
                      }
                    });
                  },
                  title: Text(
                    partNumber,
                    style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 4),
                      Text(
                        it['description'] ?? '',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, color: Colors.grey[700]),
                      ),
                      const SizedBox(height: 6),
                      Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: [
                          _badge(it['category'] ?? '—', Colors.purple),
                          _badge('GTIN: ${it['gtin'] ?? ''}', Colors.blueGrey),
                          if (it['rom_gb'] != null)
                            _badge('${it['rom_gb']}GB', Colors.orange),
                          if (it['cpu_model'] != null)
                            _badge(it['cpu_model'], Colors.green),
                        ],
                      ),
                    ],
                  ),
                  activeColor: Colors.purple,
                  controlAffinity: ListTileControlAffinity.leading,
                ),
              );
            },
          ),
        ),
        const SizedBox(height: 12),

        ElevatedButton(
          onPressed: _isLoading ? null : _generate,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.purple,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: _isLoading
              ? const SizedBox(
                  height: 24,
                  width: 24,
                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                )
              : Text(
                  'Сгенерировать выбранные (${_selectedParts.length})',
                  style: const TextStyle(fontSize: 16),
                ),
        ),
      ],
    );
  }

  Widget _badge(String text, MaterialColor color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.shade50,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(fontSize: 11, color: color.shade700),
      ),
    );
  }
}

// ============================================================
// ЭКРАН РЕЗУЛЬТАТА
// ============================================================

class CzCardsResultScreen extends StatefulWidget {
  final String sessionId;
  final Map<String, dynamic> files;

  const CzCardsResultScreen({
    super.key,
    required this.sessionId,
    required this.files,
  });

  @override
  State<CzCardsResultScreen> createState() => _CzCardsResultScreenState();
}

class _CzCardsResultScreenState extends State<CzCardsResultScreen> {
  bool _isDownloading = false;

  Future<void> _download() async {
    setState(() => _isDownloading = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final response = await api.downloadCzCards(widget.sessionId);

      final bytes = response.data as List<int>;
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', 'cz_cards_${widget.sessionId.substring(0, 8)}.zip')
        ..click();
      html.Url.revokeObjectURL(url);

      if (!mounted) return;
      setState(() => _isDownloading = false);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Архив скачан'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isDownloading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Карточки ЧЗ'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.check_circle, color: Colors.green.shade500, size: 48),
              ),
              const SizedBox(height: 24),
              const Text(
                'Готово!',
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 16),

              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.grey.shade50,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: widget.files.entries.map((e) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          const Icon(Icons.insert_drive_file_outlined,
                              size: 18, color: Colors.grey),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              e.key,
                              style: const TextStyle(fontSize: 13),
                            ),
                          ),
                          Text(
                            '${e.value} шт.',
                            style: TextStyle(
                              fontSize: 13,
                              color: Colors.purple.shade700,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    );
                  }).toList(),
                ),
              ),

              const SizedBox(height: 32),

              ElevatedButton.icon(
                onPressed: _isDownloading ? null : _download,
                icon: const Icon(Icons.download),
                label: const Text(
                  'Скачать архив',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purple,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () => Navigator.popUntil(context, (r) => r.isFirst),
                child: const Text('На главную'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}