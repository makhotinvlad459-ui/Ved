// frontend/lib/screens/category_edit_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

class CategoryEditScreen extends StatefulWidget {
  final int? categoryId;

  const CategoryEditScreen({super.key, this.categoryId});

  @override
  State<CategoryEditScreen> createState() => _CategoryEditScreenState();
}

class _CategoryEditScreenState extends State<CategoryEditScreen> {
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isNew = false;
  String _error = '';

  final TextEditingController _nameController = TextEditingController();
  final TextEditingController _nameEngController = TextEditingController();
  final TextEditingController _prefixRuController = TextEditingController();
  final TextEditingController _prefixEngController = TextEditingController();

  bool _collectSerials = true;
  String _serialSource = 'serial_number';
  bool _cleanSerialPrefix = true;

  @override
  void initState() {
    super.initState();
    _isNew = widget.categoryId == null;
    if (_isNew) {
      _isLoading = false;
    } else {
      _load();
    }
  }

  @override
  void dispose() {
    _nameController.dispose();
    _nameEngController.dispose();
    _prefixRuController.dispose();
    _prefixEngController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final cat = await api.getCategory(widget.categoryId!);

      if (!mounted) return;
      setState(() {
        _nameController.text = cat['name'] ?? '';
        _nameEngController.text = cat['name_eng'] ?? '';
        _prefixRuController.text = cat['prefix_ru'] ?? '';
        _prefixEngController.text = cat['prefix_eng'] ?? '';
        _collectSerials = cat['collect_serials'] ?? true;
        _serialSource = cat['serial_source'] ?? 'serial_number';
        _cleanSerialPrefix = cat['clean_serial_prefix'] ?? true;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Ошибка загрузки: $e';
      });
    }
  }

  Future<void> _save() async {
    final name = _nameController.text.trim();
    final prefixRu = _prefixRuController.text.trim();

    if (name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Введите название категории'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    if (prefixRu.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Введите префикс (рус)'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);

      if (_isNew) {
        await api.createFullCategory(
          name: name,
          nameEng: _nameEngController.text.trim(),
          prefixRu: prefixRu,
          prefixEng: _prefixEngController.text.trim(),
          collectSerials: _collectSerials,
          serialSource: _serialSource,
          cleanSerialPrefix: _cleanSerialPrefix,
        );
      } else {
        await api.updateCategory(
          id: widget.categoryId!,
          name: name,
          nameEng: _nameEngController.text.trim(),
          prefixRu: prefixRu,
          prefixEng: _prefixEngController.text.trim(),
          collectSerials: _collectSerials,
          serialSource: _serialSource,
          cleanSerialPrefix: _cleanSerialPrefix,
        );
      }

      if (!mounted) return;
      setState(() => _isSaving = false);

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_isNew ? '✅ Категория создана' : '✅ Категория сохранена'),
          backgroundColor: Colors.green,
        ),
      );

      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Ошибка: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _confirmAndSave() async {
    if (!_isNew) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Подтверждение'),
          content: const Text(
            'Смена префикса затронет ВСЕ товары этой категории. Продолжить?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Отмена'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Продолжить'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
    }
    await _save();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isNew ? 'Новая категория' : 'Категория'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context, false),
        ),
      ),
      body: _buildBody(),
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

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          controller: _nameController,
          decoration: const InputDecoration(
            labelText: 'Название (рус) *',
            hintText: 'Ноутбуки Lenovo',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),

        TextField(
          controller: _nameEngController,
          decoration: const InputDecoration(
            labelText: 'Название (англ)',
            hintText: 'Lenovo Laptop',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),

        TextField(
          controller: _prefixRuController,
          maxLines: 2,
          decoration: const InputDecoration(
            labelText: 'Префикс (рус) *',
            hintText: 'Портативный персональный компьютер торговой марки Lenovo',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),

        TextField(
          controller: _prefixEngController,
          maxLines: 2,
          decoration: const InputDecoration(
            labelText: 'Префикс (англ)',
            hintText: 'Portable personal computer brand Lenovo',
            border: OutlineInputBorder(),
          ),
        ),
        const SizedBox(height: 16),

        SwitchListTile(
          value: _collectSerials,
          onChanged: (v) => setState(() => _collectSerials = v),
          title: const Text('Собирать серийные номера'),
          contentPadding: EdgeInsets.zero,
        ),

        if (_collectSerials) ...[
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: _serialSource,
            decoration: const InputDecoration(
              labelText: 'Источник серийников',
              border: OutlineInputBorder(),
            ),
            items: const [
              DropdownMenuItem(
                value: 'serial_number',
                child: Text('Serial Number'),
              ),
              DropdownMenuItem(
                value: 'imei_1',
                child: Text('IMEI 1'),
              ),
            ],
            onChanged: (v) {
              if (v != null) setState(() => _serialSource = v);
            },
          ),
        ],

        const SizedBox(height: 8),
        SwitchListTile(
          value: _cleanSerialPrefix,
          onChanged: (v) => setState(() => _cleanSerialPrefix = v),
          title: const Text('Убирать префикс "S" у серийников'),
          subtitle: const Text(
            'Для Apple — да. Для Lenovo/Samsung — нет.',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          contentPadding: EdgeInsets.zero,
        ),
        const SizedBox(height: 24),

        ElevatedButton(
          onPressed: _isSaving ? null : _confirmAndSave,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.blueGrey,
            foregroundColor: Colors.white,
            padding: const EdgeInsets.symmetric(vertical: 16),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: _isSaving
              ? const SizedBox(
                  height: 24,
                  width: 24,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  ),
                )
              : Text(
                  _isNew ? 'Создать' : 'Сохранить',
                  style: const TextStyle(fontSize: 16),
                ),
        ),
      ],
    );
  }
}