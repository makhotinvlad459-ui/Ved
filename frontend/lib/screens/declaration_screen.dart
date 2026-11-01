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
          _textResult = '';
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

      final result = await api.getDeclarationText(
        bytes: bytes,
        fileName: _invoiceResult!.files.single.name,
      );

      if (!mounted) return;
      setState(() {
        _textResult = result['text'] ?? 'Нет данных';
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

  void _copyText() {
    Clipboard.setData(ClipboardData(text: _textResult));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('✅ Текст скопирован!'), backgroundColor: Colors.green),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final isDark = theme.brightness == Brightness.dark;

    // Адаптивные цвета
    final cardBg = scheme.surfaceContainerHighest;
    final resultBg = scheme.surfaceContainerLow;
    final borderColor = scheme.outlineVariant;
    final mutedText = scheme.onSurfaceVariant;

    return Scaffold(
      // AppBar без ручных цветов — берёт из темы автоматически
      appBar: AppBar(
        title: const Text('Декларирование'),
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
            Text(
              'Загрузка инвойса',
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.bold,
                color: scheme.onSurface, // явный цвет — иначе в тёмной теме может пропасть
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Выберите инвойс — мы извлечем модели и сформируем текст для письма.',
              style: TextStyle(color: mutedText),
            ),
            const SizedBox(height: 24),

            GestureDetector(
              onTap: _pickFile,
              child: Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: cardBg,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: _invoiceResult != null ? scheme.primary : borderColor,
                    width: _invoiceResult != null ? 2 : 1,
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: scheme.primary.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(Icons.description, color: scheme.primary),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('Инвойс (xlsx)',
                              style: TextStyle(fontSize: 14, color: mutedText)),
                          Text(
                            _invoiceResult?.files.single.name ?? 'Нажмите для выбора',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                              color: _invoiceResult != null
                                  ? scheme.onSurface
                                  : mutedText,
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
                backgroundColor: scheme.primary,
                foregroundColor: scheme.onPrimary,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              child: _isLoading
                  ? SizedBox(
                      height: 24,
                      width: 24,
                      child: CircularProgressIndicator(
                          color: scheme.onPrimary, strokeWidth: 2),
                    )
                  : const Text('Сгенерировать текст',
                      style: TextStyle(fontSize: 16)),
            ),

            if (_textResult.isNotEmpty) ...[
              const SizedBox(height: 32),
              Row(
                children: [
                  Text(
                    'Результат:',
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: scheme.onSurface,
                    ),
                  ),
                  const Spacer(),
                  ElevatedButton.icon(
                    onPressed: _copyText,
                    icon: const Icon(Icons.copy, size: 18),
                    label: const Text('Скопировать'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isDark
                          ? Colors.teal.shade400
                          : Colors.teal,
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
                    color: resultBg,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: borderColor),
                  ),
                  child: SingleChildScrollView(
                    child: SelectableText(
                      _textResult,
                      // ЯВНО задаём цвет — иначе в тёмной теме текст не видно
                      style: TextStyle(
                        fontSize: 15,
                        height: 1.6,
                        fontFamily: 'monospace',
                        color: scheme.onSurface,
                      ),
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