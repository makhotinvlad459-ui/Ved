// frontend/lib/screens/upload_screen.dart
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import 'pending_models_screen.dart';

class UploadScreen extends StatefulWidget {
  const UploadScreen({super.key});

  @override
  State<UploadScreen> createState() => _UploadScreenState();
}

class _UploadScreenState extends State<UploadScreen> {
  FilePickerResult? _invoiceResult;
  FilePickerResult? _manifestResult;
  FilePickerResult? _templateResult;
  String _specNumber = '';
  bool _isLoading = false;
  String _sessionId = '';

  Future<void> _pickFile(String type) async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx'],
      );

      if (result != null && result.files.single.bytes != null) {
        setState(() {
          if (type == 'invoice') {
            _invoiceResult = result;
          } else if (type == 'manifest') {
            _manifestResult = result;
          } else if (type == 'template') {
            _templateResult = result;
          }
        });
        print('✅ Выбран файл: ${result.files.single.name}');
      } else {
        print('❌ Файл не выбран или пустой');
      }
    } catch (e) {
      print('❌ Ошибка выбора файла: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка: $e')),
      );
    }
  }

  Future<void> _upload() async {
    if (_invoiceResult == null || _manifestResult == null || _templateResult == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Выберите все три файла!'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final invoiceBytes = _invoiceResult!.files.single.bytes;
    final manifestBytes = _manifestResult!.files.single.bytes;
    final templateBytes = _templateResult!.files.single.bytes;

    if (invoiceBytes == null || manifestBytes == null || templateBytes == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Ошибка чтения файлов!'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);

      final result = await api.uploadFiles(
        invoiceBytes: invoiceBytes,
        invoiceName: _invoiceResult!.files.single.name,
        manifestBytes: manifestBytes,
        manifestName: _manifestResult!.files.single.name,
        templateBytes: templateBytes,
        templateName: _templateResult!.files.single.name,
        specNumber: _specNumber,
      );

      setState(() {
        _sessionId = result['session_id'];
        _isLoading = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Файлы загружены! ID: ${_sessionId.substring(0, 8)}'),
          backgroundColor: Colors.green,
        ),
      );

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => StatusScreen(sessionId: _sessionId),
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
        title: const Text('Генерация спецификации'),
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
              'Загрузка файлов',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Выберите инвойс, манифест и шаблон спецификации',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),

            _buildFilePicker(
              label: 'Инвойс',
              result: _invoiceResult,
              icon: Icons.receipt_long,
              color: Colors.blue,
              onTap: () => _pickFile('invoice'),
            ),
            const SizedBox(height: 12),

            _buildFilePicker(
              label: 'Манифест',
              result: _manifestResult,
              icon: Icons.list_alt,
              color: Colors.orange,
              onTap: () => _pickFile('manifest'),
            ),
            const SizedBox(height: 12),

            _buildFilePicker(
              label: 'Шаблон',
              result: _templateResult,
              icon: Icons.description,
              color: Colors.green,
              onTap: () => _pickFile('template'),
            ),
            const SizedBox(height: 24),

            TextField(
              decoration: const InputDecoration(
                labelText: 'Номер спецификации (опционально)',
                border: OutlineInputBorder(),
              ),
              onChanged: (value) => _specNumber = value,
            ),
            const SizedBox(height: 24),

            ElevatedButton(
              onPressed: _isLoading ? null : _upload,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Colors.blue,
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

  Widget _buildFilePicker({
    required String label,
    required FilePickerResult? result,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    final fileName = result?.files.single.name;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: fileName != null ? color : Colors.grey.shade300,
            width: fileName != null ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 14,
                      color: Colors.grey,
                    ),
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
              Icon(
                Icons.check_circle,
                color: color,
                size: 24,
              )
            else
              Icon(
                Icons.upload_file,
                color: Colors.grey.shade400,
                size: 24,
              ),
          ],
        ),
      ),
    );
  }
}

// ============================================================
// ЭКРАН СТАТУСА
// ============================================================
class StatusScreen extends StatefulWidget {
  final String sessionId;
  const StatusScreen({super.key, required this.sessionId});

  @override
  State<StatusScreen> createState() => _StatusScreenState();
}

class _StatusScreenState extends State<StatusScreen> {
  String _status = 'pending';
  String _error = '';
  bool _isLoading = true;
  bool _isCompleted = false;
  int _attempts = 0;
  String? _specNumber;

  @override
  void initState() {
    super.initState();
    _checkStatus();
  }

  Future<void> _checkStatus() async {
    try {
      _attempts++;
      print('🔄 Проверка статуса #$_attempts для ${widget.sessionId}');
      
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.getStatus(widget.sessionId);
      
      print('📊 Статус: ${result['status']}');
      print('📊 Номер спецификации: ${result['spec_number']}');
      
      setState(() {
        _status = result['status'] ?? 'unknown';
        _error = result['errors'] ?? '';
        _isLoading = false;
        _specNumber = result['spec_number'] ?? '';
        
        if (_status == 'completed') {
          _isCompleted = true;
        }
      });

      if (_status == 'completed') {
        print('✅ Готово!');
        return;
      }

      if (_status == 'error') {
        print('❌ Ошибка: $_error');
        return;
      }

      if (_status == 'pending_models' || _status == 'pending_approval') {
        print('⚠️ Требуется подтверждение новых моделей');
        return;
      }

      if (_status == 'pending' || _status == 'processing') {
        await Future.delayed(const Duration(seconds: 2));
        if (mounted) {
          _checkStatus();
        }
      }
    } catch (e) {
      print('❌ Ошибка запроса: $e');
      setState(() {
        _isLoading = false;
        _error = 'Ошибка соединения с сервером: $e';
      });
      
      await Future.delayed(const Duration(seconds: 3));
      if (mounted && _status != 'completed' && _status != 'error') {
        _checkStatus();
      }
    }
  }

  Future<void> _download() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final response = await api.downloadResult(widget.sessionId);
      
      final bytes = response.data as List<int>;
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', 'specification_${widget.sessionId.substring(0, 8)}.xlsx')
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Статус обработки'),
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
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_isLoading) ...[
              const CircularProgressIndicator(),
              const SizedBox(height: 20),
              const Text('Проверка статуса...'),
            ] else if (_status == 'error') ...[
              const Icon(Icons.error, color: Colors.red, size: 64),
              const SizedBox(height: 20),
              const Text(
                'Ошибка обработки',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Text(
                _error,
                style: const TextStyle(color: Colors.red),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Назад'),
              ),
            ] else if (_status == 'pending_models' || _status == 'pending_approval') ...[
              const Icon(Icons.warning, color: Colors.orange, size: 64),
              const SizedBox(height: 20),
              const Text(
                'Требуется подтверждение',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              const Text(
                'Обнаружены новые модели. Подтвердите их для продолжения.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => PendingModelsScreen(
                        sessionId: widget.sessionId,
                      ),
                    ),
                  ).then((_) => _checkStatus());
                },
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                ),
                child: const Text('📋 Перейти к подтверждению'),
              ),
              const SizedBox(height: 10),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('На главную'),
              ),
            ] else if (_isCompleted) ...[
              const Icon(Icons.check_circle, color: Colors.green, size: 64),
              const SizedBox(height: 20),
              const Text(
                'Готово!',
                style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              Text(
                'Сессия: ${widget.sessionId.substring(0, 8)}...',
                style: const TextStyle(color: Colors.grey),
              ),
              if (_specNumber != null && _specNumber!.isNotEmpty)
                Text(
                  'Номер спецификации: $_specNumber',
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
                child: const Text('📥 Скачать спецификацию'),
              ),
              const SizedBox(height: 10),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('На главную'),
              ),
            ] else ...[
              const CircularProgressIndicator(),
              const SizedBox(height: 20),
              Text(
                'Обработка сессии: ${widget.sessionId.substring(0, 8)}...',
                style: const TextStyle(fontSize: 16),
              ),
              const SizedBox(height: 10),
              const Text(
                'Пожалуйста, подождите...',
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 10),
              Text(
                'Статус: $_status',
                style: const TextStyle(color: Colors.grey, fontSize: 12),
              ),
              const SizedBox(height: 10),
              TextButton(
                onPressed: () {
                  setState(() {
                    _isLoading = true;
                    _checkStatus();
                  });
                },
                child: const Text('🔄 Проверить снова'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}