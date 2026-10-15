// frontend/lib/screens/product_edit_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import 'category_edit_screen.dart';

class ProductEditScreen extends StatefulWidget {
  final int? productId;

  const ProductEditScreen({super.key, this.productId});

  @override
  State<ProductEditScreen> createState() => _ProductEditScreenState();
}

class _ProductEditScreenState extends State<ProductEditScreen> {
  bool _isLoading = true;
  bool _isSaving = false;
  bool _isNew = false;
  String _error = '';

  // Контроллеры полей
  final _partNumberController = TextEditingController();
  final _modelNumberController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _cooController = TextEditingController();
  final _weightController = TextEditingController();
  final _nameRuController = TextEditingController();
  final _upcController = TextEditingController();

  int? _selectedCategoryId;
  int? _selectedColorId;
  bool _isActive = true;

  List<dynamic> _categories = [];
  List<dynamic> _colors = [];

  @override
  void initState() {
    super.initState();
    _isNew = widget.productId == null;
    _load();
  }

  @override
  void dispose() {
    _partNumberController.dispose();
    _modelNumberController.dispose();
    _descriptionController.dispose();
    _cooController.dispose();
    _weightController.dispose();
    _nameRuController.dispose();
    _upcController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);

      // Загружаем категории и цвета
      final catsColors = await api.getCategoriesAndColors();
      _categories = catsColors['categories'] ?? [];
      _colors = catsColors['colors'] ?? [];

      if (!_isNew) {
        final p = await api.getProduct(widget.productId!);
        _partNumberController.text = p['part_number'] ?? '';
        _modelNumberController.text = p['model_number'] ?? '';
        _descriptionController.text = p['description'] ?? '';
        _cooController.text = p['coo'] ?? '';
        _weightController.text =
            p['weight'] != null ? p['weight'].toString() : '';
        _nameRuController.text = p['custom_name_ru'] ?? '';
        _upcController.text = p['upc'] ?? '';
        _selectedCategoryId = p['category_id'];
        _selectedColorId = p['color_id'];
        _isActive = p['is_active'] ?? true;
      }

      if (!mounted) return;
      setState(() {
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

  Future<void> _reloadCategoriesAndColors() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final catsColors = await api.getCategoriesAndColors();
      if (!mounted) return;
      setState(() {
        _categories = catsColors['categories'] ?? [];
        _colors = catsColors['colors'] ?? [];
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка обновления списков: $e')),
      );
    }
  }

  Future<void> _save() async {
    final partNumber = _partNumberController.text.trim();
    final modelNumber = _modelNumberController.text.trim();

    if (partNumber.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Введите артикул (part_number)'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }
    if (modelNumber.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Введите модель (model_number)'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);

      final weightText = _weightController.text.trim();
      double? weight;
      if (weightText.isNotEmpty) {
        weight = double.tryParse(weightText.replaceAll(',', '.'));
        if (weight == null) throw Exception('Неверный формат веса');
      }

      if (_isNew) {
        await api.createProduct(
          partNumber: partNumber,
          modelNumber: modelNumber,
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
          coo: _cooController.text.trim().isEmpty
              ? null
              : _cooController.text.trim(),
          upc: _upcController.text.trim().isEmpty
              ? null
              : _upcController.text.trim(),
          weight: weight,
          categoryId: _selectedCategoryId,
          colorId: _selectedColorId,
          customNameRu: _nameRuController.text.trim().isEmpty
              ? null
              : _nameRuController.text.trim(),
        );
      } else {
        await api.updateProduct(
          id: widget.productId!,
          partNumber: partNumber,
          modelNumber: modelNumber,
          description: _descriptionController.text.trim().isEmpty
              ? null
              : _descriptionController.text.trim(),
          coo: _cooController.text.trim().isEmpty
              ? null
              : _cooController.text.trim(),
          upc: _upcController.text.trim().isEmpty
              ? null
              : _upcController.text.trim(),
          weight: weight,
          categoryId: _selectedCategoryId,
          colorId: _selectedColorId,
          customNameRu: _nameRuController.text.trim().isEmpty
              ? null
              : _nameRuController.text.trim(),
          isActive: _isActive,
        );
      }

      if (!mounted) return;
      setState(() => _isSaving = false);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Сохранено'),
          backgroundColor: Colors.green,
        ),
      );

      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _delete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Удалить товар?'),
        content: Text('Товар «${_partNumberController.text}» будет скрыт.'),
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
      await api.deleteProduct(widget.productId!);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🗑️ Товар удалён'),
          backgroundColor: Colors.orange,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('❌ Ошибка: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _openCategoryEditor({int? categoryId}) async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CategoryEditScreen(categoryId: categoryId),
      ),
    );
    if (result == true) {
      await _reloadCategoriesAndColors();
    }
  }

  Future<void> _openColorEditor() async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => _QuickColorDialog(),
    );
    if (result == true) {
      await _reloadCategoriesAndColors();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isNew ? 'Новый товар' : 'Товар'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context, false),
        ),
        actions: [
          if (!_isNew)
            IconButton(
              icon: const Icon(Icons.delete_outline, color: Colors.red),
              onPressed: _delete,
            ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error.isNotEmpty
              ? Center(
                  child:
                      Text(_error, style: const TextStyle(color: Colors.red)),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    TextField(
                      controller: _partNumberController,
                      decoration: const InputDecoration(
                        labelText: 'Артикул (part_number) *',
                        hintText: 'MGEA4LL/A',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),

                    TextField(
                      controller: _modelNumberController,
                      decoration: const InputDecoration(
                        labelText: 'Модель / артикул модели (model_number) *',
                        hintText: 'A3428',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),

                    TextField(
                      controller: _descriptionController,
                      maxLines: 3,
                      decoration: const InputDecoration(
                        labelText: 'Описание (description)',
                        hintText:
                            'Apple MacBook Pro 16" Space Black (M5 Pro 18C CPU, 20C GPU/24Gb/1Tb SSD) (MGEA4LL/A)',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _cooController,
                            decoration: const InputDecoration(
                              labelText: 'Страна (COO)',
                              hintText: 'China',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _weightController,
                            keyboardType: const TextInputType.numberWithOptions(
                                decimal: true),
                            decoration: const InputDecoration(
                              labelText: 'Вес, кг',
                              hintText: '3.9',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    TextField(
                      controller: _upcController,
                      decoration: const InputDecoration(
                        labelText: 'UPC',
                        hintText: '195950714746',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),

                    // === КАТЕГОРИЯ ===
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<int?>(
                            initialValue: _selectedCategoryId,
                            isExpanded: true,
                            decoration: const InputDecoration(
                              labelText: 'Категория',
                              border: OutlineInputBorder(),
                            ),
                            items: [
                              const DropdownMenuItem<int?>(
                                value: null,
                                child: Text('Без категории'),
                              ),
                              ..._categories.map((c) {
                                return DropdownMenuItem<int?>(
                                  value: c['id'] as int,
                                  child: Text(c['name'] ?? ''),
                                );
                              }),
                            ],
                            onChanged: (value) {
                              setState(() => _selectedCategoryId = value);
                            },
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add_circle_outline,
                              color: Colors.blueGrey),
                          tooltip: 'Создать категорию',
                          onPressed: () => _openCategoryEditor(),
                        ),
                      ],
                    ),
                    if (_selectedCategoryId != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 4, left: 4),
                        child: TextButton.icon(
                          onPressed: () => _openCategoryEditor(
                              categoryId: _selectedCategoryId),
                          icon: const Icon(Icons.edit, size: 14),
                          label: const Text(
                            'Редактировать категорию',
                            style: TextStyle(fontSize: 12),
                          ),
                        ),
                      ),
                    const SizedBox(height: 12),

                    // === ЦВЕТ ===
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<int?>(
                            initialValue: _selectedColorId,
                            isExpanded: true,
                            decoration: const InputDecoration(
                              labelText: 'Цвет',
                              border: OutlineInputBorder(),
                            ),
                            items: [
                              const DropdownMenuItem<int?>(
                                value: null,
                                child: Text('Без цвета'),
                              ),
                              ..._colors.map((c) {
                                return DropdownMenuItem<int?>(
                                  value: c['id'] as int,
                                  child: Text('${c['rus']} (${c['eng']})'),
                                );
                              }),
                            ],
                            onChanged: (value) {
                              setState(() => _selectedColorId = value);
                            },
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.add_circle_outline,
                              color: Colors.blueGrey),
                          tooltip: 'Создать цвет',
                          onPressed: _openColorEditor,
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    // === CUSTOM NAME RU ===
                    TextField(
                      controller: _nameRuController,
                      maxLines: 2,
                      decoration: const InputDecoration(
                        labelText: 'Название (рус)',
                        hintText: 'Apple MacBook Pro 16" "Черный"',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),

                    if (!_isNew)
                      SwitchListTile(
                        value: _isActive,
                        onChanged: (v) => setState(() => _isActive = v),
                        title: const Text('Активен'),
                        subtitle:
                            const Text('Неактивные не участвуют в обработке'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    const SizedBox(height: 16),

                    ElevatedButton(
                      onPressed: _isSaving ? null : _save,
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
                ),
    );
  }
}

// ============================================================
// ДИАЛОГ БЫСТРОГО СОЗДАНИЯ ЦВЕТА
// ============================================================

class _QuickColorDialog extends StatefulWidget {
  @override
  State<_QuickColorDialog> createState() => _QuickColorDialogState();
}

class _QuickColorDialogState extends State<_QuickColorDialog> {
  final _engController = TextEditingController();
  final _rusController = TextEditingController();
  bool _isSaving = false;
  String _error = '';

  @override
  void dispose() {
    _engController.dispose();
    _rusController.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final eng = _engController.text.trim();
    final rus = _rusController.text.trim();

    if (eng.isEmpty || rus.isEmpty) {
      setState(() => _error = 'Заполните оба поля');
      return;
    }

    setState(() {
      _isSaving = true;
      _error = '';
    });

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      await api.createColor(eng: eng, rus: rus);
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
    return AlertDialog(
      title: const Text('Новый цвет'),
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
            controller: _rusController,
            decoration: const InputDecoration(
              labelText: 'Название (рус)',
              hintText: 'Пурпурный',
              border: OutlineInputBorder(),
            ),
          ),
          if (_error.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(_error,
                style: const TextStyle(color: Colors.red, fontSize: 13)),
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
            backgroundColor: Colors.blueGrey,
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
              : const Text('Создать'),
        ),
      ],
    );
  }
}