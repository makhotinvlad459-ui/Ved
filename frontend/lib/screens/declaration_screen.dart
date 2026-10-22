import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';
import 'package:flutter/services.dart';
import '../services/api_service.dart';

class DeclarationScreen extends StatefulWidget {
  const DeclarationScreen({super.key});

  @override
  State<DeclarationScreen> createState() => _DeclarationScreenState();
}

class _DeclarationScreenState extends State<DeclarationScreen> {
  FilePickerResult? _invoiceResult;
  bool _isLoading = false;
  String _sessionId = '';
  String _textResult = '';

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx'],
      );
      if (result != null && result.files.single.bytes != null) {
        setState(() {
          _invoiceResult = result;
          _textResult = ''; // сброс
          _sessionId = '';
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

  Future<void> _uploadAndProcess() async {
    if (_invoiceResult == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Выберите инвойс'), backgroundColor: Colors.red),
      );
      return;
    }

    final bytes = _invoiceResult!.files.single.bytes;
    if (bytes == null) return;

    setState(() => _isLoading = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      
      // Отправляем инвойс 3 раза, чтобы пройти валидацию эндпоинта /upload/
      final result = await api.uploadFiles(
        invoiceBytes: bytes,
        invoiceName: _invoiceResult!.files.single.name,
        manifestBytes: bytes, // заглушка
        manifestName: _invoiceResult!.files.single.name,
        templateBytes: bytes, // заглушка
        templateName: _invoiceResult!.files.single.name,
        specNumber: 'DECL',
      );

      final sessionId = result['session_id'];

      // Ждем завершения Celery (или pending_approval)
      await _waitForCompletion(sessionId);

      // Получаем текст
      final textResult = await api.getTextSummary(sessionId);
      
      if (!mounted) return;
      setState(() {
        _sessionId = sessionId;
        _textResult = textResult['text'] ?? 'Нет данных';
        _isLoading = false;
      });
      
    } catch (e) {
      if (!mounted) return;
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _waitForCompletion(String sessionId) async {
    final api = Provider.of<ApiService>(context, listen: false);
    while (true) {
      await Future.delayed(const Duration(seconds: 2));
      final statusData = await api.getStatus(sessionId);
      final status = statusData['status'];
      if (status == 'completed' || status == 'pending_approval' || status == 'error') {
        break;
      }
    }
  }

  void _copyText() {
    Clipboard.setData(ClipboardData(text: _textResult));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('✅ Текст скопирован!'), backgroundColor: Colors.green),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Декларирование'),
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
              'Загрузка инвойса',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Выберите инвойс — мы извлечем модели и сформируем текст для письма.',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),

            GestureDetector(
              onTap: _pickFile,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _invoiceResult != null ? Colors.blue : Colors.grey.shade300,
                    width: _invoiceResult != null ? 2 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(Icons.description, color: Colors.blue),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Инвойс (xlsx)', style: TextStyle(fontSize: 14, color: Colors.grey)),
                          Text(
                            _invoiceResult?.files.single.name ?? 'Нажмите для выбора',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: _invoiceResult != null ? Colors.black : Colors.grey,
                            ),
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
              onPressed: _isLoading ? null : _uploadAndProcess,
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: Colors.blue,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: _isLoading
                  ? const SizedBox(height: 24, width: 24, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Text('Сгенерировать текст', style: TextStyle(fontSize: 16)),
            ),

            if (_textResult.isNotEmpty) ...[
              const SizedBox(height: 32),
              Row(
                children: [
                  const Text(
                    'Результат:',
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const Spacer(),
                  ElevatedButton.icon(
                    onPressed: _copyText,
                    icon: const Icon(Icons.copy, size: 18),
                    label: const Text('Скопировать'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.teal,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Expanded(
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade50,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: Colors.grey.shade300),
                  ),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      _textResult,
                      style: const TextStyle(fontSize: 15, height: 1.6, fontFamily: 'monospace'),
                    ),
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