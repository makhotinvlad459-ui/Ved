// frontend/lib/screens/cz_upload_screen.dart
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

class CzUploadScreen extends StatefulWidget {
  const CzUploadScreen({super.key});

  @override
  State<CzUploadScreen> createState() => _CzUploadScreenState();
}

class _CzUploadScreenState extends State<CzUploadScreen> {
  FilePickerResult? _invoiceResult;
  FilePickerResult? _specResult;
  FilePickerResult? _czResult;
  bool _isLoading = false;
  String _sessionId = '';

  Future<void> _pickFile(String type) async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx'],
      );
      if (result != null && result.files.single.bytes != null) {
        setState(() {
          if (type == 'invoice') {
            _invoiceResult = result;
          } else if (type == 'spec') {
            _specResult = result;
          } else if (type == 'cz') {
            _czResult = result;
          }
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

  Future<void> _upload() async {
    if (_invoiceResult == null || _specResult == null || _czResult == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Выберите все три файла!'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final invoiceBytes = _invoiceResult!.files.single.bytes;
    final specBytes = _specResult!.files.single.bytes;
    final czBytes = _czResult!.files.single.bytes;

    if (invoiceBytes == null || specBytes == null || czBytes == null) {
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
      final result = await api.uploadCzFiles(
        invoiceBytes: invoiceBytes,
        invoiceName: _invoiceResult!.files.single.name,
        specBytes: specBytes,
        specName: _specResult!.files.single.name,
        czBytes: czBytes,
        czName: _czResult!.files.single.name,
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

      if (!mounted) return;
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => CzStatusScreen(sessionId: _sessionId),
        ),
      );
    } catch (e) {
      setState(() => _isLoading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Загрузка кодов ЧЗ'),
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
              'Инвойс + Спецификация + Файл кодов ЧЗ',
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
              label: 'Спецификация',
              result: _specResult,
              icon: Icons.description,
              color: Colors.green,
              onTap: () => _pickFile('spec'),
            ),
            const SizedBox(height: 12),
            _buildFilePicker(
              label: 'Файл кодов ЧЗ',
              result: _czResult,
              icon: Icons.qr_code_2,
              color: Colors.purple,
              onTap: () => _pickFile('cz'),
            ),
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
                  Text(label,
                      style: const TextStyle(fontSize: 14, color: Colors.grey)),
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
              Icon(Icons.check_circle, color: color, size: 24)
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
  String? _specNumber;

  @override
  void initState() {
    super.initState();
    _checkStatus();
  }

  Future<void> _checkStatus() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.getCzStatus(widget.sessionId);

      setState(() {
        _status = result['status'] ?? 'unknown';
        _error = result['errors'] ?? '';
        _specNumber = result['spec_number'];
        _isLoading = false;
        if (_status == 'completed') _isCompleted = true;
      });

      if (_status == 'completed' || _status == 'error') return;

      if (_status == 'pending' || _status == 'processing') {
        await Future.delayed(const Duration(seconds: 2));
        if (mounted) _checkStatus();
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = 'Ошибка: $e';
      });
    }
  }

  Future<void> _download() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final response = await api.downloadCzResult(widget.sessionId);

      final bytes = response.data as List<int>;
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final name = 'ЧЗ - код №${_specNumber ?? widget.sessionId.substring(0, 8)}.xlsx';
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', name)
        ..click();
      html.Url.revokeObjectUrl(url);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Файл скачан!'),
          backgroundColor: Colors.green,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Статус обработки ЧЗ'),
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
              const Text('Обработка...'),
            ] else if (_status == 'error') ...[
              const Icon(Icons.error, color: Colors.red, size: 64),
              const SizedBox(height: 20),
              const Text('Ошибка обработки',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              const SizedBox(height: 10),
              Text(_error,
                  style: const TextStyle(color: Colors.red),
                  textAlign: TextAlign.center),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Назад'),
              ),
            ] else if (_isCompleted) ...[
              const Icon(Icons.check_circle, color: Colors.green, size: 64),
              const SizedBox(height: 20),
              const Text('Готово!',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
              if (_specNumber != null)
                Text('Номер спецификации: $_specNumber',
                    style: const TextStyle(color: Colors.grey)),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: _download,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.purple,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(horizontal: 40, vertical: 16),
                ),
                child: const Text('📥 Скачать файл'),
              ),
            ] else ...[
              const CircularProgressIndicator(),
              const SizedBox(height: 20),
              Text('Статус: $_status',
                  style: const TextStyle(color: Colors.grey, fontSize: 12)),
            ],
          ],
        ),
      ),
    );
  }
}