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
      _showError('Введите артикул (part_number)');
      return;
    }
    // model_number обязательно ТОЛЬКО при создании
    if (_isNew && modelNumber.isEmpty) {
      _showError('Введите модель (model_number)');
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
          modelNumber: modelNumber.isEmpty ? null : modelNumber,
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
      _showError('❌ Ошибка: $e');
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), backgroundColor: Colors.red),
    );
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
      _showError('❌ Ошибка: $e');
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

  String _categoryLabel(Map<String, dynamic>? c) {
    if (c == null) return '';
    return (c['name'] ?? '').toString();
  }

  String _colorLabel(Map<String, dynamic>? c) {
    if (c == null) return '';
    final rus = c['rus'] ?? '';
    final eng = c['eng'] ?? '';
    if (eng.toString().isEmpty) return rus.toString();
    return '$rus ($eng)';
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
                      decoration: InputDecoration(
                        labelText: _isNew
                            ? 'Модель / артикул модели (model_number) *'
                            : 'Модель / артикул модели (model_number)',
                        hintText: 'A3428',
                        border: const OutlineInputBorder(),
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

                    Row(
                      children: [
                        Expanded(child: _buildCategoryAutocomplete()),
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

                    Row(
                      children: [
                        Expanded(child: _buildColorAutocomplete()),
                        IconButton(
                          icon: const Icon(Icons.add_circle_outline,
                              color: Colors.blueGrey),
                          tooltip: 'Создать цвет',
                          onPressed: _openColorEditor,
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

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

  Widget _buildCategoryAutocomplete() {
    final selectedCat = _selectedCategoryId != null
        ? _categories.firstWhere(
            (c) => c['id'] == _selectedCategoryId,
            orElse: () => null,
          )
        : null;

    return Autocomplete<Map<String, dynamic>>(
      key: ValueKey('cat_${_selectedCategoryId}'),
      initialValue: TextEditingValue(
        text: _categoryLabel(selectedCat),
      ),
      optionsBuilder: (TextEditingValue value) {
        if (value.text.isEmpty) {
          return _categories.cast<Map<String, dynamic>>();
        }
        final q = value.text.toLowerCase();
        return _categories
            .cast<Map<String, dynamic>>()
            .where((c) =>
                (c['name'] ?? '').toString().toLowerCase().contains(q))
            .toList();
      },
      displayStringForOption: (option) => _categoryLabel(option),
      onSelected: (option) {
        setState(() {
          _selectedCategoryId = option['id'] as int;
        });
      },
      fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
        return TextField(
          controller: controller,
          focusNode: focusNode,
          decoration: InputDecoration(
            labelText: 'Категория',
            hintText: 'Начните вводить название',
            border: const OutlineInputBorder(),
            prefixIcon: const Icon(Icons.category_outlined),
            suffixIcon: _selectedCategoryId != null
                ? IconButton(
                    icon: const Icon(Icons.clear, size: 18),
                    onPressed: () {
                      setState(() {
                        _selectedCategoryId = null;
                      });
                    },
                  )
                : null,
          ),
          onSubmitted: (_) => onFieldSubmitted(),
        );
      },
      optionsViewBuilder: (context, onSelected, options) {
        return _buildAutocompleteOptions(
          options: options,
          onSelected: onSelected,
          labelBuilder: _categoryLabel,
          width: 400,
        );
      },
    );
  }

  Widget _buildColorAutocomplete() {
    final selectedColor = _selectedColorId != null
        ? _colors.firstWhere(
            (c) => c['id'] == _selectedColorId,
            orElse: () => null,
          )
        : null;

    return Autocomplete<Map<String, dynamic>>(
      key: ValueKey('color_${_selectedColorId}'),
      initialValue: TextEditingValue(
        text: _colorLabel(selectedColor),
      ),
      optionsBuilder: (TextEditingValue value) {
        if (value.text.isEmpty) {
          return _colors.cast<Map<String, dynamic>>();
        }
        final q = value.text.toLowerCase();
        return _colors.cast<Map<String, dynamic>>().where((c) {
          final rus = (c['rus'] ?? '').toString().toLowerCase();
          final eng = (c['eng'] ?? '').toString().toLowerCase();
          return rus.contains(q) || eng.contains(q);
        }).toList();
      },
      displayStringForOption: (option) => _colorLabel(option),
      onSelected: (option) {
        setState(() {
          _selectedColorId = option['id'] as int;
        });
      },
      fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
        return TextField(
          controller: controller,
          focusNode: focusNode,
          decoration: InputDecoration(
            labelText: 'Цвет',
            hintText: 'Начните вводить название',
            border: const OutlineInputBorder(),
            prefixIcon: const Icon(Icons.palette),
            suffixIcon: _selectedColorId != null
                ? IconButton(
                    icon: const Icon(Icons.clear, size: 18),
                    onPressed: () {
                      setState(() {
                        _selectedColorId = null;
                      });
                    },
                  )
                : null,
          ),
          onSubmitted: (_) => onFieldSubmitted(),
        );
      },
      optionsViewBuilder: (context, onSelected, options) {
        return _buildAutocompleteOptions(
          options: options,
          onSelected: onSelected,
          labelBuilder: _colorLabel,
          width: 400,
        );
      },
    );
  }

  Widget _buildAutocompleteOptions({
    required Iterable<Map<String, dynamic>> options,
    required void Function(Map<String, dynamic>) onSelected,
    required String Function(Map<String, dynamic>?) labelBuilder,
    double width = 400,
  }) {
    return Align(
      alignment: Alignment.topLeft,
      child: Material(
        elevation: 4,
        borderRadius: BorderRadius.circular(8),
        child: ConstrainedBox(
          constraints: BoxConstraints(maxHeight: 300, maxWidth: width),
          child: ListView.builder(
            padding: EdgeInsets.zero,
            shrinkWrap: true,
            itemCount: options.length,
            itemBuilder: (context, index) {
              final option = options.elementAt(index);
              return InkWell(
                onTap: () => onSelected(option),
                child: Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  child: Text(labelBuilder(option)),
                ),
              );
            },
          ),
        ),
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