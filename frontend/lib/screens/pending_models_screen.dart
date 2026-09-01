// frontend/lib/screens/pending_models_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';

class PendingModelsScreen extends StatefulWidget {
  final String sessionId;
  const PendingModelsScreen({super.key, required this.sessionId});

  @override
  State<PendingModelsScreen> createState() => _PendingModelsScreenState();
}

class _PendingModelsScreenState extends State<PendingModelsScreen> {
  List<dynamic> _models = [];
  List<dynamic> _categories = [];
  List<dynamic> _colors = [];
  bool _isLoading = true;
  String _error = '';

  final Map<int, TextEditingController> _categoryNameController = {};
  final Map<int, TextEditingController> _categoryPrefixController = {};
  final Map<int, TextEditingController> _colorRusController = {};
  final Map<int, TextEditingController> _colorEngController = {};
  final Map<int, TextEditingController> _nameRuController = {};
  final Map<int, String?> _selectedCategory = {};
  final Map<int, String?> _selectedColor = {};

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  @override
  void dispose() {
    for (var c in _categoryNameController.values) c.dispose();
    for (var c in _categoryPrefixController.values) c.dispose();
    for (var c in _colorRusController.values) c.dispose();
    for (var c in _colorEngController.values) c.dispose();
    for (var c in _nameRuController.values) c.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);

      final data = await api.getCategoriesAndColors();
      setState(() {
        _categories = data['categories'] ?? [];
        _colors = data['colors'] ?? [];
      });

      final models = await api.getPendingModels(widget.sessionId);
      setState(() {
        _models = models;
        _isLoading = false;
      });

      for (var model in _models) {
        final id = model['id'];
        if (model['suggested_category_id'] != null) {
          _selectedCategory[id] = model['suggested_category_id'].toString();
        } else {
          _selectedCategory[id] = 'new';
        }
        if (model['suggested_color_id'] != null) {
          _selectedColor[id] = model['suggested_color_id'].toString();
        }
        _categoryNameController[id] = TextEditingController();
        _categoryPrefixController[id] = TextEditingController();
        _colorRusController[id] = TextEditingController();
        _colorEngController[id] = TextEditingController();
        _nameRuController[id] = TextEditingController(
          text: model['suggested_name_ru'] ?? '',
        );
      }
    } catch (e) {
      setState(() {
        _error = 'Ошибка загрузки: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _approveModel(Map<String, dynamic> model) async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final id = model['id'];

      String? categoryId = _selectedCategory[id];
      String? colorId = _selectedColor[id];
      String? newCategoryName;
      String? newCategoryPrefix;
      String? newColorRus;
      String? newColorEng;

      // Если выбрана новая категория
      if (categoryId == 'new') {
        newCategoryName = _categoryNameController[id]?.text.trim();
        newCategoryPrefix = _categoryPrefixController[id]?.text.trim();
        
        if (newCategoryName == null || newCategoryName.isEmpty) {
          _showToast('Введите название новой категории');
          return;
        }
        if (newCategoryPrefix == null || newCategoryPrefix.isEmpty) {
          _showToast('Введите префикс для новой категории');
          return;
        }
        
        // Создаём категорию через API
        final newCat = await api.createCategory(
          name: newCategoryName,
          prefixRu: newCategoryPrefix,
        );
        categoryId = newCat['id'].toString();
      }

      // Если выбран новый цвет
      if (colorId == 'new') {
        newColorRus = _colorRusController[id]?.text.trim();
        newColorEng = _colorEngController[id]?.text.trim();
        if (newColorRus == null || newColorRus.isEmpty ||
            newColorEng == null || newColorEng.isEmpty) {
          _showToast('Введите название цвета на русском и английском');
          return;
        }
        final newColor = await api.createColor(eng: newColorEng, rus: newColorRus);
        colorId = newColor['id'].toString();
      }

      // Получаем название товара (без префикса!)
      final nameRu = _nameRuController[id]?.text.trim() ?? model['suggested_name_ru'] ?? '';

      // Подтверждаем модель
      await api.approveModel(
        sessionId: widget.sessionId,
        pendingId: id,
        customNameRu: nameRu,
        customCategoryId: categoryId != null ? int.parse(categoryId) : null,
        customColorId: colorId != null ? int.parse(colorId) : null,
      );

      setState(() {
        _models.remove(model);
      });

      _showToast('✅ Модель подтверждена', isSuccess: true);

      if (_models.isEmpty) {
        Navigator.pop(context, true);
      }
    } catch (e) {
      _showToast('❌ Ошибка: $e');
    }
  }

  Future<void> _approveAll() async {
    for (var model in _models) {
      await _approveModel(model);
    }
  }

  void _showToast(String message, {bool isSuccess = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isSuccess ? Colors.green : Colors.red,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Новые модели'),
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
            const Text(
              'Обнаружены новые модели',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              'Подтвердите добавление моделей в базу данных',
              style: TextStyle(color: Colors.grey[600]),
            ),
            const SizedBox(height: 16),

            if (_isLoading) ...[
              const Expanded(
                child: Center(child: CircularProgressIndicator()),
              ),
            ] else if (_error.isNotEmpty) ...[
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error, color: Colors.red, size: 48),
                      const SizedBox(height: 16),
                      Text(_error, textAlign: TextAlign.center),
                    ],
                  ),
                ),
              ),
            ] else if (_models.isEmpty) ...[
              const Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.check_circle, color: Colors.green, size: 48),
                      SizedBox(height: 16),
                      Text('Все модели уже подтверждены'),
                    ],
                  ),
                ),
              ),
            ] else ...[
              Expanded(
                child: ListView.builder(
                  itemCount: _models.length,
                  itemBuilder: (context, index) {
                    final model = _models[index];
                    final id = model['id'];

                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Заголовок
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    model['part_number'] ?? '',
                                    style: const TextStyle(
                                      fontWeight: FontWeight.bold,
                                      fontSize: 16,
                                    ),
                                  ),
                                ),
                                TextButton(
                                  onPressed: () => _approveModel(model),
                                  child: const Text('✅ Добавить'),
                                ),
                              ],
                            ),
                            const SizedBox(height: 4),
                            Text(
                              model['description'] ?? '',
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(color: Colors.grey[600]),
                            ),
                            const SizedBox(height: 12),

                            // Категория
                            _buildCategoryDropdown(id),
                            const SizedBox(height: 8),

                            // Поля для новой категории
                            if (_selectedCategory[id] == 'new')
                              Column(
                                children: [
                                  TextField(
                                    controller: _categoryNameController[id],
                                    decoration: const InputDecoration(
                                      labelText: 'Название новой категории',
                                      hintText: 'Например: Роботы',
                                      border: OutlineInputBorder(),
                                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    ),
                                    style: const TextStyle(fontSize: 14),
                                  ),
                                  const SizedBox(height: 8),
                                  TextField(
                                    controller: _categoryPrefixController[id],
                                    decoration: const InputDecoration(
                                      labelText: 'Префикс новой категории (рус)',
                                      hintText: 'Например: Робот-пылесос торговой марки',
                                      border: OutlineInputBorder(),
                                      contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                    ),
                                    style: const TextStyle(fontSize: 14),
                                  ),
                                ],
                              ),
                            const SizedBox(height: 8),

                            // Цвет
                            _buildColorDropdown(id),
                            const SizedBox(height: 8),

                            // Поля для нового цвета
                            if (_selectedColor[id] == 'new')
                              Row(
                                children: [
                                  Expanded(
                                    child: TextField(
                                      controller: _colorRusController[id],
                                      decoration: const InputDecoration(
                                        labelText: 'Цвет (рус)',
                                        hintText: 'Розовое золото',
                                        border: OutlineInputBorder(),
                                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                      ),
                                      style: const TextStyle(fontSize: 14),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: TextField(
                                      controller: _colorEngController[id],
                                      decoration: const InputDecoration(
                                        labelText: 'Цвет (англ)',
                                        hintText: 'Rose Gold',
                                        border: OutlineInputBorder(),
                                        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                      ),
                                      style: const TextStyle(fontSize: 14),
                                    ),
                                  ),
                                ],
                              ),
                            const SizedBox(height: 8),

                            // Название товара (БЕЗ ПРЕФИКСА!)
                            TextField(
                              controller: _nameRuController[id],
                              decoration: const InputDecoration(
                                labelText: 'Название товара (без префикса)',
                                hintText: 'Apple Watch Series 11',
                                border: OutlineInputBorder(),
                                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                              ),
                              style: const TextStyle(fontSize: 14),
                            ),
                            if (_selectedCategory[id] != 'new' && _selectedCategory[id] != null)
                              Padding(
                                padding: const EdgeInsets.only(top: 4),
                                child: Text(
                                  '🔹 Префикс будет добавлен автоматически: ${_getCategoryPrefix(int.parse(_selectedCategory[id]!))}',
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: Colors.green[700],
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _approveAll,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 16),
                ),
                child: Text('✅ Подтвердить все (${_models.length})'),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _getCategoryPrefix(int categoryId) {
    final category = _categories.firstWhere(
      (c) => c['id'] == categoryId,
      orElse: () => null,
    );
    return category != null ? (category['prefix_ru'] ?? '') : '';
  }

  Widget _buildCategoryDropdown(int id) {
    final items = <DropdownMenuItem<String>>[
      const DropdownMenuItem(value: 'new', child: Text('➕ Новая категория')),
    ];

    final uniqueCategories = <int, dynamic>{};
    for (var cat in _categories) {
      uniqueCategories[cat['id']] = cat;
    }

    for (var cat in uniqueCategories.values) {
      final value = cat['id'].toString();
      items.add(
        DropdownMenuItem(
          value: value,
          child: Text(
            '${cat['name']} ${cat['prefix_ru']?.isNotEmpty == true ? '(${cat['prefix_ru']})' : ''}',
          ),
        ),
      );
    }

    return DropdownButtonFormField<String?>(
      value: _selectedCategory[id],
      items: items,
      onChanged: (value) {
        setState(() {
          _selectedCategory[id] = value;
        });
      },
      decoration: const InputDecoration(
        labelText: 'Категория',
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
    );
  }

  Widget _buildColorDropdown(int id) {
    final items = <DropdownMenuItem<String>>[
      const DropdownMenuItem(value: '', child: Text('Без цвета')),
      const DropdownMenuItem(value: 'new', child: Text('➕ Новый цвет')),
    ];

    final uniqueColors = <int, dynamic>{};
    for (var color in _colors) {
      uniqueColors[color['id']] = color;
    }

    for (var color in uniqueColors.values) {
      final value = color['id'].toString();
      items.add(
        DropdownMenuItem(
          value: value,
          child: Text('${color['rus']} (${color['eng']})'),
        ),
      );
    }

    return DropdownButtonFormField<String?>(
      value: _selectedColor[id],
      items: items,
      onChanged: (value) {
        setState(() {
          _selectedColor[id] = value;
        });
      },
      decoration: const InputDecoration(
        labelText: 'Цвет',
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
    );
  }
}