// frontend/lib/screens/cz_colors_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

class CzColorsScreen extends StatefulWidget {
  const CzColorsScreen({super.key});

  @override
  State<CzColorsScreen> createState() => _CzColorsScreenState();
}

class _CzColorsScreenState extends State<CzColorsScreen> {
  final TextEditingController _searchController = TextEditingController();
  Timer? _debounce;

  List<dynamic> _colors = [];
  bool _isLoading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
  }

  void _onSearchChanged(String value) {
    if (_debounce?.isActive ?? false) _debounce!.cancel();
    _debounce = Timer(const Duration(milliseconds: 300), () {
      _load(query: value);
    });
  }

  Future<void> _load({String query = ''}) async {
    setState(() {
      _isLoading = true;
      _error = '';
    });

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final data = await api.getCzColorMappings(query: query);
      if (!mounted) return;
      setState(() {
        _colors = data;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Ошибка: $e';
      });
    }
  }

  Future<void> _openEditor({Map<String, dynamic>? existing}) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => _ColorEditDialog(existing: existing),
    );
    if (result == true) _load(query: _searchController.text);
  }

  Future<void> _delete(Map<String, dynamic> color) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Удалить цвет?'),
        content: Text('«${color['eng']}» → ${color['cz_value']}'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Удалить', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      await api.deleteCzColorMapping(color['id']);
      _load(query: _searchController.text);
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
        title: const Text('Цвета ЧЗ'),
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
            TextField(
              controller: _searchController,
              onChanged: _onSearchChanged,
              decoration: InputDecoration(
                hintText: 'Поиск: eng или значение ЧЗ',
                prefixIcon: const Icon(Icons.search),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Найдено: ${_colors.length}',
                    style: const TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: () => _openEditor(),
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Добавить'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.purple,
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Expanded(child: _buildBody()),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error.isNotEmpty) {
      return Center(
        child: Text(_error, style: const TextStyle(color: Colors.red)),
      );
    }
    if (_colors.isEmpty) {
      return const Center(
        child: Text('Ничего не найдено', style: TextStyle(color: Colors.grey)),
      );
    }

    return ListView.builder(
      itemCount: _colors.length,
      itemBuilder: (context, index) {
        final c = _colors[index];
        final isActive = c['is_active'] ?? true;

        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: ListTile(
            onTap: () => _openEditor(existing: c),
            title: Text(
              c['eng'] ?? '',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Text('→ ${c['cz_value'] ?? ''}'),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (!isActive)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: const Text(
                      'удалён',
                      style: TextStyle(fontSize: 10, color: Colors.red),
                    ),
                  ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, color: Colors.red),
                  onPressed: () => _delete(c),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

// ============================================================
// ДИАЛОГ РЕДАКТИРОВАНИЯ
// ============================================================

class _ColorEditDialog extends StatefulWidget {
  final Map<String, dynamic>? existing;

  const _ColorEditDialog({this.existing});

  @override
  State<_ColorEditDialog> createState() => _ColorEditDialogState();
}

class _ColorEditDialogState extends State<_ColorEditDialog> {
  final _engController = TextEditingController();
  final _czController = TextEditingController();
  bool _isSaving = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    if (widget.existing != null) {
      _engController.text = widget.existing!['eng'] ?? '';
      _czController.text = widget.existing!['cz_value'] ?? '';
    }
  }

  @override
  void dispose() {
    _engController.dispose();
    _czController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final eng = _engController.text.trim();
    final cz = _czController.text.trim().toUpperCase();

    if (eng.isEmpty || cz.isEmpty) {
      setState(() => _error = 'Заполните оба поля');
      return;
    }

    setState(() {
      _isSaving = true;
      _error = '';
    });

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      if (widget.existing == null) {
        await api.createCzColorMapping(eng: eng, czValue: cz);
      } else {
        await api.updateCzColorMapping(
          id: widget.existing!['id'],
          eng: eng,
          czValue: cz,
        );
      }
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isSaving = false;
        _error = '$e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isNew = widget.existing == null;

    return AlertDialog(
      title: Text(isNew ? 'Новый цвет' : 'Редактирование цвета'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            controller: _engController,
            decoration: const InputDecoration(
              labelText: 'Название (eng)',
              hintText: 'Magenta',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _czController,
            textCapitalization: TextCapitalization.characters,
            decoration: const InputDecoration(
              labelText: 'Значение ЧЗ',
              hintText: 'ПУРПУРНЫЙ',
              border: OutlineInputBorder(),
            ),
          ),
          if (_error.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(_error, style: const TextStyle(color: Colors.red, fontSize: 13)),
          ],
        ],
      ),
      actions: [
        TextButton(
          onPressed: _isSaving ? null : () => Navigator.pop(context, false),
          child: const Text('Отмена'),
        ),
        ElevatedButton(
          onPressed: _isSaving ? null : _save,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.purple,
            foregroundColor: Colors.white,
          ),
          child: _isSaving
              ? const SizedBox(
                  height: 20,
                  width: 20,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  ),
                )
              : Text(isNew ? 'Создать' : 'Сохранить'),
        ),
      ],
    );
  }
}