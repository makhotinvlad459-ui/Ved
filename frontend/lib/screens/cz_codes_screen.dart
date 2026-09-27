// frontend/lib/screens/cz_codes_screen.dart
import 'dart:html' as html;
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

class CzCodesScreen extends StatefulWidget {
  const CzCodesScreen({super.key});

  @override
  State<CzCodesScreen> createState() => _CzCodesScreenState();
}

class _CzCodesScreenState extends State<CzCodesScreen> {
  FilePickerResult? _czSpecResult;
  bool _isLoading = false;
  String _sessionId = '';

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['xlsx'],
      );
      if (result != null && result.files.single.bytes != null) {
        setState(() {
          _czSpecResult = result;
        });
        print('✅ Выбран файл: ${result.files.single.name}');
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
    if (_czSpecResult == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Выберите файл ЧЗ-спецификации!'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    final bytes = _czSpecResult!.files.single.bytes;
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
      final result = await api.uploadCzCodes(
        czSpecBytes: bytes,
        czSpecName: _czSpecResult!.files.single.name,
      );

      setState(() {
        _sessionId = result['session_id'];
        _isLoading = false;
      });

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('✅ Файл загружен! ID: ${_sessionId.substring(0, 8)}'),
          backgroundColor: Colors.green,
        ),
      );

      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (context) => CzCodesStatusScreen(sessionId: _sessionId),
        ),
      );
    } catch (e) {
      setState(() => _isLoading = false);
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
        title: const Text('Коды ЧЗ для ввода'),
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
            Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Colors.indigo.shade600, Colors.indigo.shade300],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.indigo.shade100,
                        blurRadius: 12,
                        offset: const Offset(0, 4),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.qr_code_scanner,
                    color: Colors.white,
                    size: 30,
                  ),
                ),
                const SizedBox(width: 16),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Коды ЧЗ для ввода',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      SizedBox(height: 4),
                      Text(
                        'Разделение кодов по категориям и странам',
                        style: TextStyle(color: Colors.grey, fontSize: 14),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 32),

            const Text(
              'Загрузка файла',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const Text(
              'Выберите файл «ЧЗ - код №…», из него будут извлечены '
              'коды для MacBook, iPad и iPhone',
              style: TextStyle(color: Colors.grey, fontSize: 13),
            ),
            const SizedBox(height: 16),

            _buildFilePicker(),
            const SizedBox(height: 32),

            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              height: 56,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(12),
                gradient: _isLoading
                    ? null
                    : LinearGradient(
                        colors: [Colors.indigo.shade600, Colors.indigo.shade400],
                        begin: Alignment.centerLeft,
                        end: Alignment.centerRight,
                      ),
                boxShadow: _isLoading
                    ? null
                    : [
                        BoxShadow(
                          color: Colors.indigo.shade200,
                          blurRadius: 12,
                          offset: const Offset(0, 4),
                        ),
                      ],
              ),
              child: ElevatedButton(
                onPressed: _isLoading ? null : _upload,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  foregroundColor: Colors.white,
                  shadowColor: Colors.transparent,
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
                        'Сформировать файлы',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilePicker() {
    final fileName = _czSpecResult?.files.single.name;
    final hasFile = fileName != null;

    return GestureDetector(
      onTap: _pickFile,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: hasFile ? Colors.indigo.shade50 : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: hasFile ? Colors.indigo : Colors.grey.shade300,
            width: hasFile ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.03),
              blurRadius: 8,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: hasFile
                    ? Colors.indigo.withOpacity(0.15)
                    : Colors.grey.shade100,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(
                hasFile ? Icons.check_circle : Icons.upload_file,
                color: hasFile ? Colors.indigo : Colors.grey.shade500,
                size: 28,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Файл ЧЗ-спецификации',
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
    );
  }
}

// ============================================================
// ЭКРАН СТАТУСА
// ============================================================
class CzCodesStatusScreen extends StatefulWidget {
  final String sessionId;
  const CzCodesStatusScreen({super.key, required this.sessionId});

  @override
  State<CzCodesStatusScreen> createState() => _CzCodesStatusScreenState();
}

class _CzCodesStatusScreenState extends State<CzCodesStatusScreen> {
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
      final result = await api.getCzCodesStatus(widget.sessionId);

      if (!mounted) return;
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
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Ошибка: $e';
      });
    }
  }

  Future<void> _download() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final response = await api.downloadCzCodes(widget.sessionId);

      final bytes = response.data as List<int>;
      final blob = html.Blob([bytes]);
      final url = html.Url.createObjectUrlFromBlob(blob);
      final name = 'ЧЗ_ввод_№${_specNumber ?? widget.sessionId.substring(0, 8)}.zip';
      final anchor = html.AnchorElement(href: url)
        ..setAttribute('download', name)
        ..click();
      html.Url.revokeObjectUrl(url);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Архив скачан!'),
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
        title: const Text('Коды ЧЗ для ввода'),
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
              if (_isLoading) ...[
                const SizedBox(
                  height: 64,
                  width: 64,
                  child: CircularProgressIndicator(
                    strokeWidth: 3,
                    color: Colors.indigo,
                  ),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Готовим коды ЧЗ...',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Разделяем коды по категориям и странам',
                  style: TextStyle(color: Colors.grey, fontSize: 13),
                ),
              ] else if (_status == 'error') ...[
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: Colors.red.shade50,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.error_outline,
                      color: Colors.red.shade400, size: 48),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Ошибка',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Text(
                    _error,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  ),
                ),
                const SizedBox(height: 24),
                ElevatedButton(
                  onPressed: () => Navigator.pop(context),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.grey.shade700,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 40, vertical: 16),
                  ),
                  child: const Text('Назад'),
                ),
              ] else if (_isCompleted) ...[
                Container(
                  width: 80,
                  height: 80,
                  decoration: BoxDecoration(
                    color: Colors.green.shade50,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(Icons.check_circle,
                      color: Colors.green.shade500, size: 48),
                ),
                const SizedBox(height: 24),
                const Text(
                  'Готово!',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                if (_specNumber != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 8),
                    decoration: BoxDecoration(
                      color: Colors.indigo.shade50,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'ЧЗ_ввод_№$_specNumber.zip',
                      style: TextStyle(
                        color: Colors.indigo.shade700,
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                      ),
                    ),
                  ),
                const SizedBox(height: 32),
                ElevatedButton.icon(
                  onPressed: _download,
                  icon: const Icon(Icons.download),
                  label: const Text(
                    'Скачать архив',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.indigo,
                    foregroundColor: Colors.white,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 40, vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('На главную'),
                ),
              ] else ...[
                const SizedBox(
                  height: 64,
                  width: 64,
                  child: CircularProgressIndicator(
                    strokeWidth: 3,
                    color: Colors.indigo,
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  'Статус: $_status',
                  style: const TextStyle(color: Colors.grey, fontSize: 13),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}