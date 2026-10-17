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

  final Map<int, int?> _selectedCategory = {};
  final Map<int, int?> _selectedColor = {};

  final Map<int, bool> _isNewCategory = {};
  final Map<int, bool> _isNewColor = {};

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
      _categories = data['categories'] ?? [];
      _colors = data['colors'] ?? [];

      final models = await api.getPendingModels(widget.sessionId);

      setState(() {
        _models = models;
        _isLoading = false;
      });

      for (var model in _models) {
        final id = model['id'];
        _selectedCategory[id] = model['suggested_category_id'];
        _selectedColor[id] = model['suggested_color_id'];
        _isNewCategory[id] = false;
        _isNewColor[id] = false;

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

      int? categoryId = _selectedCategory[id];
      int? colorId = _selectedColor[id];

      if (_isNewCategory[id] == true) {
        final name = _categoryNameController[id]?.text.trim();
        final prefix = _categoryPrefixController[id]?.text.trim();
        if (name == null || name.isEmpty) {
          _showToast('Введите название новой категории');
          return;
        }
        if (prefix == null || prefix.isEmpty) {
          _showToast('Введите префикс для новой категории');
          return;
        }
        final newCat = await api.createCategory(name: name, prefixRu: prefix);
        categoryId = newCat['id'];
        _categories.add(newCat);
        _isNewCategory[id] = false;
      }

      if (_isNewColor[id] == true) {
        final rus = _colorRusController[id]?.text.trim();
        final eng = _colorEngController[id]?.text.trim();
        if (rus == null || rus.isEmpty || eng == null || eng.isEmpty) {
          _showToast('Введите название цвета на русском и английском');
          return;
        }
        final newColor = await api.createColor(eng: eng, rus: rus);
        colorId = newColor['id'];
        _colors.add(newColor);
        _isNewColor[id] = false;
      }

      final nameRu = _nameRuController[id]?.text.trim() ??
          model['suggested_name_ru'] ??
          '';

      await api.approveModel(
        sessionId: widget.sessionId,
        pendingId: id,
        customNameRu: nameRu,
        customCategoryId: categoryId,
        customColorId: colorId,
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

  void _showToast(String message, {bool isSuccess = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: isSuccess ? Colors.green : Colors.red,
      ),
    );
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
        title: const Text('Новые модели'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SelectionArea(
        child: Padding(
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

              if (_isLoading)
                const Expanded(
                  child: Center(child: CircularProgressIndicator()),
                )
              else if (_error.isNotEmpty)
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
                )
              else if (_models.isEmpty)
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
                )
              else
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
                                  if (model['type'] == 'missing_category')
                                    Container(
                                      padding: const EdgeInsets.symmetric(
                                          horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: Colors.orange.shade50,
                                        borderRadius:
                                            BorderRadius.circular(6),
                                      ),
                                      child: Text(
                                        'нет категории',
                                        style: TextStyle(
                                          color: Colors.orange.shade700,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ),
                                  const SizedBox(width: 8),
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

                              _buildCategoryAutocomplete(id),
                              if (_isNewCategory[id] == true) ...[
                                const SizedBox(height: 8),
                                TextField(
                                  controller: _categoryNameController[id],
                                  decoration: const InputDecoration(
                                    labelText: 'Название новой категории',
                                    hintText: 'Например: Роботы',
                                    border: OutlineInputBorder(),
                                    contentPadding: EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 8),
                                  ),
                                  style: const TextStyle(fontSize: 14),
                                ),
                                const SizedBox(height: 8),
                                TextField(
                                  controller: _categoryPrefixController[id],
                                  decoration: const InputDecoration(
                                    labelText: 'Префикс (рус)',
                                    hintText:
                                        'Например: Робот-пылесос торговой марки',
                                    border: OutlineInputBorder(),
                                    contentPadding: EdgeInsets.symmetric(
                                        horizontal: 12, vertical: 8),
                                  ),
                                  style: const TextStyle(fontSize: 14),
                                ),
                              ],
                              const SizedBox(height: 8),

                              _buildColorAutocomplete(id),
                              if (_isNewColor[id] == true) ...[
                                const SizedBox(height: 8),
                                Row(
                                  children: [
                                    Expanded(
                                      child: TextField(
                                        controller: _colorRusController[id],
                                        decoration: const InputDecoration(
                                          labelText: 'Цвет (рус)',
                                          hintText: 'Розовое золото',
                                          border: OutlineInputBorder(),
                                          contentPadding:
                                              EdgeInsets.symmetric(
                                                  horizontal: 12,
                                                  vertical: 8),
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
                                          contentPadding:
                                              EdgeInsets.symmetric(
                                                  horizontal: 12,
                                                  vertical: 8),
                                        ),
                                        style: const TextStyle(fontSize: 14),
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                              const SizedBox(height: 8),

                              TextField(
                                controller: _nameRuController[id],
                                decoration: const InputDecoration(
                                  labelText:
                                      'Название товара (без префикса)',
                                  hintText: 'Apple Watch Series 11',
                                  border: OutlineInputBorder(),
                                  contentPadding: EdgeInsets.symmetric(
                                      horizontal: 12, vertical: 8),
                                ),
                                style: const TextStyle(fontSize: 14),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // AUTOCOMPLETE — КАТЕГОРИЯ
  // ============================================================

  Widget _buildCategoryAutocomplete(int id) {
    final selectedCat = _selectedCategory[id] != null
        ? _categories.firstWhere(
            (c) => c['id'] == _selectedCategory[id],
            orElse: () => null,
          )
        : null;

    return Autocomplete<Map<String, dynamic>>(
      key: ValueKey('cat_${id}_${_selectedCategory[id]}'),
      initialValue: TextEditingValue(text: _categoryLabel(selectedCat)),
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
          _selectedCategory[id] = option['id'] as int;
          _isNewCategory[id] = false;
        });
      },
      fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
        return TextField(
          controller: controller,
          focusNode: focusNode,
          decoration: InputDecoration(
            labelText: 'Категория',
            hintText: 'Начните вводить или создайте новую',
            border: const OutlineInputBorder(),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            prefixIcon: const Icon(Icons.category_outlined, size: 18),
            suffixIcon: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_selectedCategory[id] != null)
                  IconButton(
                    icon: const Icon(Icons.clear, size: 18),
                    onPressed: () {
                      setState(() {
                        _selectedCategory[id] = null;
                        controller.clear();
                      });
                    },
                  ),
                IconButton(
                  icon: Icon(
                    _isNewCategory[id] == true
                        ? Icons.close
                        : Icons.add_circle_outline,
                    size: 18,
                  ),
                  tooltip: _isNewCategory[id] == true
                      ? 'Отменить создание'
                      : 'Создать новую категорию',
                  onPressed: () {
                    setState(() {
                      _isNewCategory[id] = !(_isNewCategory[id] ?? false);
                    });
                  },
                ),
              ],
            ),
          ),
          onSubmitted: (_) => onFieldSubmitted(),
        );
      },
      optionsViewBuilder: (context, onSelected, options) {
        return _buildAutocompleteOptions(
          options: options,
          onSelected: onSelected,
          labelBuilder: _categoryLabel,
        );
      },
    );
  }

  // ============================================================
  // AUTOCOMPLETE — ЦВЕТ
  // ============================================================

  Widget _buildColorAutocomplete(int id) {
    final selectedColor = _selectedColor[id] != null
        ? _colors.firstWhere(
            (c) => c['id'] == _selectedColor[id],
            orElse: () => null,
          )
        : null;

    return Autocomplete<Map<String, dynamic>>(
      key: ValueKey('color_${id}_${_selectedColor[id]}'),
      initialValue: TextEditingValue(text: _colorLabel(selectedColor)),
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
          _selectedColor[id] = option['id'] as int;
          _isNewColor[id] = false;
        });
      },
      fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
        return TextField(
          controller: controller,
          focusNode: focusNode,
          decoration: InputDecoration(
            labelText: 'Цвет',
            hintText: 'Начните вводить или создайте новый',
            border: const OutlineInputBorder(),
            contentPadding:
                const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            prefixIcon: const Icon(Icons.palette, size: 18),
            suffixIcon: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_selectedColor[id] != null)
                  IconButton(
                    icon: const Icon(Icons.clear, size: 18),
                    onPressed: () {
                      setState(() {
                        _selectedColor[id] = null;
                        controller.clear();
                      });
                    },
                  ),
                IconButton(
                  icon: Icon(
                    _isNewColor[id] == true
                        ? Icons.close
                        : Icons.add_circle_outline,
                    size: 18,
                  ),
                  tooltip: _isNewColor[id] == true
                      ? 'Отменить создание'
                      : 'Создать новый цвет',
                  onPressed: () {
                    setState(() {
                      _isNewColor[id] = !(_isNewColor[id] ?? false);
                    });
                  },
                ),
              ],
            ),
          ),
          onSubmitted: (_) => onFieldSubmitted(),
        );
      },
      optionsViewBuilder: (context, onSelected, options) {
        return _buildAutocompleteOptions(
          options: options,
          onSelected: onSelected,
          labelBuilder: _colorLabel,
        );
      },
    );
  }

  Widget _buildAutocompleteOptions({
    required Iterable<Map<String, dynamic>> options,
    required void Function(Map<String, dynamic>) onSelected,
    required String Function(Map<String, dynamic>?) labelBuilder,
  }) {
    return Align(
      alignment: Alignment.topLeft,
      child: Material(
        elevation: 4,
        borderRadius: BorderRadius.circular(8),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxHeight: 250, maxWidth: 400),
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