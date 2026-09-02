// frontend/lib/screens/packing_list_screen.dart
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';

class PackingListScreen extends StatefulWidget {
  const PackingListScreen({super.key});

  @override
  State<PackingListScreen> createState() => _PackingListScreenState();
}

class _PackingListScreenState extends State<PackingListScreen> {
  FilePickerResult? _fileResult;
  bool _isLoading = false;
  String _sessionId = '';

  Future<void> _pickFile() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx'],
      );

      if (result != null && result.files.single.bytes != null) {
        setState(() {
          _fileResult = result;
        });
        print('✅ Выбран файл: ${result.files.single.name}');
      }
    } catch (e) {
      print('❌ Ошибка выбора файла: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка: $e')),
      );
    }
  }

  Future<void> _upload() async {
    if (_fileResult == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Выберите файл!'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final bytes = _fileResult!.files.single.bytes;
    if (bytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Ошибка чтения файла!'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.uploadPackingList(
        bytes: bytes,
        fileName: _fileResult!.files.single.name,
      );

      setState(() {
        _sessionId = result['session_id'];
        _isLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Файл загружен! ID: ${_sessionId.substring(0, 8)}'),
          backgroundColor: Colors.green,
        ),
      );

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => PackingListStatusScreen(sessionId: _sessionId),
        ),
      );
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Ошибка: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Генерация Packing List'),
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Загрузка Packing List',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Выберите файл Packing List для обработки',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),

            _buildFilePicker(),
            const SizedBox(height: 24),

            ElevatedButton(
              onPressed: _isLoading ? null : _upload,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Colors.orange,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: _isLoading
                  ? const SizedBox(
                      height: 24,
                      width: 24,
                      child: CircularProgressIndicator(
                        color: Colors.white,
                        strokeWidth: 2,
                      ),
                    )
                  : const Text(
                      'Загрузить и обработать',
                      style: TextStyle(fontSize: 16),
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilePicker() {
    final fileName = _fileResult?.files.single.name;

    return GestureDetector(
      onTap: _pickFile,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: fileName != null ? Colors.orange : Colors.grey.shade300,
            width: fileName != null ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.orange.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.description, color: Colors.orange),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Файл Packing List',
                    style: TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                  Text(
                    fileName ?? 'Нажмите для выбора',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      color: fileName != null ? Colors.black : Colors.grey,
                    ),
                  ),
                ],
              ),
            ),
            if (fileName != null)
              const Icon(Icons.check_circle, color: Colors.orange, size: 24)
            else
              Icon(Icons.upload_file, color: Colors.grey.shade400, size: 24),
          ],
        ),
      ),
    );
  }
}

// ============================================================
// ЭКРАН СТАТУСА
// ============================================================
class PackingListStatusScreen extends StatefulWidget {
  final String sessionId;
  const PackingListStatusScreen({super.key, required this.sessionId});

  @override
  State<PackingListStatusScreen> createState() => _PackingListStatusScreenState();
}

class _PackingListStatusScreenState extends State<PackingListStatusScreen> {
  String _status = 'pending';
  String _error = '';
  bool _isLoading = true;
  bool _isCompleted = false;
  int _pendingCount = 0;
  List<dynamic> _pendingWeights = [];
  Map<String, List<dynamic>> _groupedWeights = {};
  final Map<String, TextEditingController> _weightControllers = {};

  @override
  void initState() {
    super.initState();
    _checkStatus();
  }

  @override
  void dispose() {
    for (var controller in _weightControllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _checkStatus() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.getPackingListStatus(widget.sessionId);

      setState(() {
        _status = result['status'] ?? 'unknown';
        _error = result['errors'] ?? '';
        _pendingCount = result['pending_weights_count'] ?? 0;
        _isLoading = false;

        if (_status == 'completed') {
          _isCompleted = true;
        }
      });

      if (_status == 'pending_weights') {
        await _loadPendingWeights();
        return;
      }

      if (_status == 'completed') {
        return;
      }

      if (_status == 'pending' || _status == 'processing') {
        await Future.delayed(const Duration(seconds: 2));
        if (mounted) {
          _checkStatus();
        }
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = 'Ошибка: $e';
      });
    }
  }

  Future<void> _loadPendingWeights() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final data = await api.getPendingWeights(widget.sessionId);
      
      // Группируем по model_number
      final Map<String, List<dynamic>> grouped = {};
      for (var item in data['pending_weights']) {
        final key = item['model_number'] ?? 'unknown';
        if (!grouped.containsKey(key)) {
          grouped[key] = [];
        }
        grouped[key]!.add(item);
      }
      
      setState(() {
        _pendingWeights = data['pending_weights'] ?? [];
        _groupedWeights = grouped;
        _isLoading = false;
      });
      
      // Создаём контроллеры для каждой группы
      for (var entry in grouped.entries) {
        if (!_weightControllers.containsKey(entry.key)) {
          _weightControllers[entry.key] = TextEditingController();
        }
      }
    } catch (e) {
      print('❌ Ошибка загрузки pending: $e');
    }
  }

  Future<void> _approveGroupWeight(String modelNumber) async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      
      final controller = _weightControllers[modelNumber];
      if (controller == null) return;
      
      final weight = double.tryParse(controller.text);
      if (weight == null || weight <= 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Введите корректный вес!'),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }
      
      // Подтверждаем все партийные номера в группе
      final items = _groupedWeights[modelNumber] ?? [];
      for (var item in items) {
        await api.approveWeight(item['id'], weight);
      }
      
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Вес для модели $modelNumber подтверждён (${items.length} артикулов)'),
          backgroundColor: Colors.green,
        ),
      );
      
      // Обновляем список
      await _loadPendingWeights();
      await _checkStatus();
      setState(() {});
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Ошибка: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _download() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final response = await api.downloadPackingList(widget.sessionId);

      final bytes = response.data as List<int>;
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', 'packing_list_${widget.sessionId.substring(0, 8)}.xlsx')
        ..click();
      html.Url.revokeObjectUrl(url);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Файл скачан!'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Ошибка скачивания: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Widget _buildGroupCard(String modelNumber, List<dynamic> items) {
    final partNumbers = items.map((i) => i['part_number']).join(', ');
    final totalQty = items.fold<int>(0, (sum, item) => sum + (item['qty'] as int? ?? 0));
    
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '📦 Модель: $modelNumber',
                    style: const TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.orange.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.orange.withOpacity(0.3)),
                  ),
                  child: Text(
                    '${items.length} артикулов',
                    style: const TextStyle(fontSize: 12, color: Colors.orange),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Артикулы: $partNumbers',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
            Text(
              'Общее количество: $totalQty шт.',
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _weightControllers[modelNumber],
                    decoration: const InputDecoration(
                      labelText: 'Вес (кг)',
                      border: OutlineInputBorder(),
                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    ),
                    keyboardType: TextInputType.number,
                  ),
                ),
                const SizedBox(width: 8),
                ElevatedButton(
                  onPressed: () => _approveGroupWeight(modelNumber),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                  ),
                  child: const Text('✅ Подтвердить все'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Статус Packing List'),
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_isLoading) ...[
              const Expanded(
                child: Center(child: CircularProgressIndicator()),
              ),
            ] else if (_status == 'error') ...[
              const Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error, color: Colors.red, size: 64),
                      SizedBox(height: 20),
                      Text('Ошибка', style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
                    ],
                  ),
                ),
              ),
            ] else if (_status == 'pending_weights') ...[
              const Icon(Icons.warning, color: Colors.orange, size: 64),
              const SizedBox(height: 20),
              const Text(
                'Требуется подтверждение весов',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Text(
                'Найдено ${_groupedWeights.keys.length} моделей без веса',
                style: const TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 20),
              Expanded(
                child: ListView.builder(
                  itemCount: _groupedWeights.keys.length,
                  itemBuilder: (context, index) {
                    final modelNumber = _groupedWeights.keys.elementAt(index);
                    final items = _groupedWeights[modelNumber] ?? [];
                    return _buildGroupCard(modelNumber, items);
                  },
                ),
              ),
            ] else if (_isCompleted) ...[
              const Icon(Icons.check_circle, color: Colors.green, size: 64),
              const SizedBox(height: 20),
              const Text(
                'Готово!',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _download,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                ),
                child: const Text('📥 Скачать Packing List'),
              ),
            ] else ...[
              const Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 20),
                      Text('Обработка...', style: TextStyle(fontSize: 16)),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}