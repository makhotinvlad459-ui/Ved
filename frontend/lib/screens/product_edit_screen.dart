// frontend/lib/screens/product_edit_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import 'category_edit_screen.dart';

class ProductEditScreen extends StatefulWidget {
  final int productId;
  const ProductEditScreen({super.key, required this.productId});

  @override
  State<ProductEditScreen> createState() => _ProductEditScreenState();
}

class _ProductEditScreenState extends State<ProductEditScreen> {
  bool _isLoading = true;
  bool _isSaving = false;
  String _error = '';

  Map<String, dynamic>? _product;
  List<dynamic> _categories = [];
  List<dynamic> _colors = [];

  final TextEditingController _weightController = TextEditingController();
  final TextEditingController _nameRuController = TextEditingController();

  int? _selectedCategoryId;
  int? _selectedColorId;
  bool _isActive = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _weightController.dispose();
    _nameRuController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);

      final product = await api.getProduct(widget.productId);
      final catsColors = await api.getCategoriesAndColors();

      if (!mounted) return;
      setState(() {
        _product = product;
        _categories = catsColors['categories'] ?? [];
        _colors = catsColors['colors'] ?? [];

        _weightController.text =
            product['weight'] != null ? product['weight'].toString() : '';
        _nameRuController.text = product['custom_name_ru'] ?? '';
        _selectedCategoryId = product['category_id'];
        _selectedColorId = product['color_id'];
        _isActive = product['is_active'] ?? true;

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
    setState(() => _isSaving = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);

      final weightText = _weightController.text.trim();
      double? weight;
      if (weightText.isNotEmpty) {
        weight = double.tryParse(weightText);
        if (weight == null) {
          throw Exception('Неверный формат веса');
        }
      }

      await api.updateProduct(
        id: widget.productId,
        weight: weight,
        categoryId: _selectedCategoryId,
        colorId: _selectedColorId,
        customNameRu: _nameRuController.text.trim(),
        isActive: _isActive,
      );

      if (!mounted) return;
      setState(() => _isSaving = false);

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('✅ Сохранено'),
          backgroundColor: Colors.green,
        ),
      );
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

  Future<void> _openCategoryEdit() async {
    if (_selectedCategoryId == null) return;

    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CategoryEditScreen(
          categoryId: _selectedCategoryId!,
        ),
      ),
    );

    if (result == true) {
      // Перезагружаем, чтобы подтянуть обновлённый префикс
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Товар'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context, true),
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
    if (_product == null) {
      return const Center(child: Text('Товар не найден'));
    }

    final p = _product!;
    final partNumber = p['part_number'] ?? '';
    final modelNumber = p['model_number'] ?? '';
    final description = p['description'] ?? '';
    final coo = p['coo'] ?? '';
    final categoryPrefix = p['category']?['prefix_ru'] ?? '';

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // === ИНФО (readonly) ===
        _readonlyBlock('Артикул', partNumber),
        _readonlyBlock('Модель', modelNumber),
        _readonlyBlock('Описание', description),
        _readonlyBlock('Страна', coo),

        const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 8),
        const Text(
          'Редактирование',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),

        // === ВЕС ===
        TextField(
          controller: _weightController,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(
            labelText: 'Вес (кг)',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.scale),
          ),
        ),
        const SizedBox(height: 16),

        // === КАТЕГОРИЯ ===
        DropdownButtonFormField<int?>(
          value: _selectedCategoryId,
          decoration: const InputDecoration(
            labelText: 'Категория',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.category),
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
            setState(() {
              _selectedCategoryId = value;
              // Обновляем префикс из выбранной категории
              final cat = _categories.firstWhere(
                (c) => c['id'] == value,
                orElse: () => null,
              );
              if (cat != null) {
                _product!['category'] = cat;
              }
            });
          },
        ),
        const SizedBox(height: 8),

        // === ПРЕФИКС (readonly) ===
        if (categoryPrefix.isNotEmpty)
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                const Icon(Icons.label_outline, size: 18, color: Colors.grey),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Префикс категории',
                        style: TextStyle(fontSize: 11, color: Colors.grey),
                      ),
                      Text(
                        categoryPrefix,
                        style: const TextStyle(fontSize: 13),
                      ),
                    ],
                  ),
                ),
                TextButton.icon(
                  onPressed: _openCategoryEdit,
                  icon: const Icon(Icons.edit, size: 16),
                  label: const Text('Изменить'),
                ),
              ],
            ),
          ),
        const SizedBox(height: 16),

        // === ЦВЕТ ===
        DropdownButtonFormField<int?>(
          value: _selectedColorId,
          decoration: const InputDecoration(
            labelText: 'Цвет',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.palette),
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
        const SizedBox(height: 16),

        // === CUSTOM NAME ===
        TextField(
          controller: _nameRuController,
          maxLines: 2,
          decoration: const InputDecoration(
            labelText: 'Название (рус)',
            border: OutlineInputBorder(),
            prefixIcon: Icon(Icons.text_fields),
          ),
        ),
        const SizedBox(height: 16),

        // === is_active ===
        SwitchListTile(
          value: _isActive,
          onChanged: (value) => setState(() => _isActive = value),
          title: const Text('Активен'),
          subtitle: const Text('Неактивные товары не участвуют в обработке'),
          contentPadding: EdgeInsets.zero,
        ),
        const SizedBox(height: 24),

        // === КНОПКА ===
        ElevatedButton(
          onPressed: _isSaving ? null : _save,
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.blue,
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
              : const Text(
                  'Сохранить',
                  style: TextStyle(fontSize: 16),
                ),
        ),
      ],
    );
  }

  Widget _readonlyBlock(String label, String value) {
    if (value.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 12, color: Colors.grey),
          ),
          const SizedBox(height: 2),
          Text(value, style: const TextStyle(fontSize: 15)),
        ],
      ),
    );
  }
}