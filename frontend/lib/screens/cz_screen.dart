// frontend/lib/screens/cz_screen.dart
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';

class CzScreen extends StatefulWidget {
  const CzScreen({super.key});

  @override
  State<CzScreen> createState() => _CzScreenState();
}

class _CzScreenState extends State<CzScreen> {
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
      final result = await api.uploadCZFile(
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
          builder: (context) => CzStatusScreen(sessionId: _sessionId),
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
        title: const Text('Честный знак'),
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
              'Загрузка кодов ЧЗ',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Выберите файл с кодами Честного знака',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),

            _buildFilePicker(),
            const SizedBox(height: 24),

            ElevatedButton(
              onPressed: _isLoading ? null : _upload,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Colors.purple,
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
            color: fileName != null ? Colors.purple : Colors.grey.shade300,
            width: fileName != null ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.purple.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.qr_code, color: Colors.purple),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Файл с кодами ЧЗ',
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
              const Icon(Icons.check_circle, color: Colors.purple, size: 24)
            else
              Icon(Icons.upload_file, color: Colors.grey.shade400, size: 24),
          ],
        ),
      ),
    );
  }
}

// ============================================================
// ЭКРАН СТАТУСА ЧЗ
// ============================================================
class CzStatusScreen extends StatefulWidget {
  final String sessionId;
  const CzStatusScreen({super.key, required this.sessionId});

  @override
  State<CzStatusScreen> createState() => _CzStatusScreenState();
}

class _CzStatusScreenState extends State<CzStatusScreen> {
  String _status = 'pending';
  String _error = '';
  bool _isLoading = true;
  bool _isCompleted = false;
  List<dynamic> _pendingGtins = [];
  final Map<int, TextEditingController> _controllers = {};

  @override
  void initState() {
    super.initState();
    _checkStatus();
  }

  @override
  void dispose() {
    for (var c in _controllers.values) c.dispose();
    super.dispose();
  }

  Future<void> _checkStatus() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.getCZStatus(widget.sessionId);

      setState(() {
        _status = result['status'] ?? 'unknown';
        _error = result['errors'] ?? '';
        _isLoading = false;

        if (_status == 'completed') {
          _isCompleted = true;
        }
      });

      if (_status == 'pending_gtins') {
        await _loadPendingGtins();
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

  Future<void> _loadPendingGtins() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final data = await api.getPendingGtins(widget.sessionId);
      setState(() {
        _pendingGtins = data['pending_gtins'] ?? [];
      });
      for (var item in _pendingGtins) {
        _controllers[item['id']] = TextEditingController();
      }
    } catch (e) {
      print('❌ Ошибка загрузки pending: $e');
    }
  }

  Future<void> _approveGtin(int pendingId) async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final c = _controllers[pendingId];
      if (c == null) return;

      // Парсим поля из строки: "Артикул, Модель, Страна, Название"
      final parts = c.text.split(',').map((s) => s.trim()).toList();
      if (parts.length < 4) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Введите: Артикул, Модель, Страна, Название'),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }

      await api.approveGtin(
        pendingId: pendingId,
        partNumber: parts[0],
        modelNumber: parts[1],
        coo: parts[2],
        productName: parts[3],
        categoryName: parts.length > 4 ? parts[4] : null,
      );

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ GTIN подтверждён'),
          backgroundColor: Colors.green,
        ),
      );

      await _loadPendingGtins();
      await _checkStatus();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Ошибка: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _skipGtin(int pendingId) async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      await api.skipGtin(pendingId);
      await _loadPendingGtins();
      await _checkStatus();
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
      final response = await api.downloadCZResult(widget.sessionId);

      final bytes = response.data as List<int>;
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', 'cz_${widget.sessionId.substring(0, 8)}.zip')
        ..click();
      html.Url.revokeObjectUrl(url);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Файлы скачаны!'),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Статус ЧЗ'),
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
                      Icon(Icons.error, color: Colors.red, size: 48),
                      SizedBox(height: 16),
                      Text('Ошибка'),
                    ],
                  ),
                ),
              ),
            ] else if (_status == 'pending_gtins') ...[
              const Icon(Icons.warning, color: Colors.orange, size: 48),
              const SizedBox(height: 16),
              const Text(
                'Требуется привязка GTIN',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 8),
              Text(
                'Найдено ${_pendingGtins.length} новых GTIN',
                style: const TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: ListView.builder(
                  itemCount: _pendingGtins.length,
                  itemBuilder: (context, index) {
                    final item = _pendingGtins[index];
                    final id = item['id'];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'GTIN: ${item['gtin']}',
                              style: const TextStyle(fontWeight: FontWeight.bold),
                            ),
                            Text('Кодов: ${item['code_count']}'),
                            Text('Предложенное имя: ${item['suggested_name'] ?? '—'}'),
                            const SizedBox(height: 8),
                            TextField(
                              controller: _controllers[id],
                              decoration: const InputDecoration(
                                labelText: 'Артикул, Модель, Страна, Название',
                                hintText: 'MGEA4LL/A, A3428, Vietnam, MacBook Pro 16',
                                border: OutlineInputBorder(),
                              ),
                            ),
                            const SizedBox(height: 8),
                            Row(
                              children: [
                                Expanded(
                                  child: ElevatedButton(
                                    onPressed: () => _approveGtin(id),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.green,
                                      foregroundColor: Colors.white,
                                    ),
                                    child: const Text('✅ Подтвердить'),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                OutlinedButton(
                                  onPressed: () => _skipGtin(id),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.red,
                                  ),
                                  child: const Text('Пропустить'),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    );
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
              const SizedBox(height: 8),
              Text(
                'Создано ${_pendingGtins.length} файлов',
                style: const TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _download,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                ),
                child: const Text('📥 Скачать ZIP'),
              ),
            ] else ...[
              const Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 16),
                      Text('Обработка...'),
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