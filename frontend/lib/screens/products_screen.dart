// frontend/lib/screens/products_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import 'product_edit_screen.dart';

class ProductsScreen extends StatefulWidget {
  const ProductsScreen({super.key});

  @override
  State<ProductsScreen> createState() => _ProductsScreenState();
}

class _ProductsScreenState extends State<ProductsScreen> {
  final TextEditingController _searchController = TextEditingController();
  Timer? _debounce;

  List<dynamic> _products = [];
  bool _isLoading = true;
  bool _hasSearched = false;
  bool _missingCategoryFilter = false;
  String _error = '';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _load();
    });
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
      final data = await api.searchProducts(
        query,
        missingCategory: _missingCategoryFilter,
      );
      if (!mounted) return;
      setState(() {
        _products = data['products'] ?? [];
        _isLoading = false;
        _hasSearched = true;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = 'Ошибка: $e';
        _hasSearched = true;
      });
    }
  }

  Future<void> _openProduct(int id) async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ProductEditScreen(productId: id),
      ),
    );
    if (result == true) _load(query: _searchController.text);
  }

  Future<void> _createNew() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const ProductEditScreen(productId: null),
      ),
    );
    if (result == true) _load(query: _searchController.text);
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Товары'),
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
                hintText: 'Поиск: артикул, модель, описание, GTIN...',
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
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                FilterChip(
                  label: const Text('Без категории'),
                  selected: _missingCategoryFilter,
                  onSelected: (v) {
                    setState(() => _missingCategoryFilter = v);
                    _load(query: _searchController.text);
                  },
                  avatar: Icon(
                    _missingCategoryFilter
                        ? Icons.check
                        : Icons.filter_alt_outlined,
                    size: 16,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    'Найдено: ${_products.length}',
                    style: TextStyle(
                      fontSize: 14,
                      color: isDark ? Colors.grey.shade400 : Colors.grey,
                    ),
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: _createNew,
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Добавить'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blueGrey,
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Expanded(child: _buildBody(isDark)),
          ],
        ),
      ),
    );
  }

  Widget _buildBody(bool isDark) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_error.isNotEmpty) {
      return Center(
        child: Text(_error, style: const TextStyle(color: Colors.red)),
      );
    }
    if (!_hasSearched) {
      return Center(
        child: Text(
          'Введите запрос для поиска',
          style: TextStyle(
            color: isDark ? Colors.grey.shade400 : Colors.grey,
            fontSize: 16,
          ),
        ),
      );
    }
    if (_products.isEmpty) {
      if (_missingCategoryFilter) {
        return Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.check_circle, color: Colors.green, size: 64),
              const SizedBox(height: 16),
              Text(
                'Товаров без категории нет',
                style: TextStyle(
                  fontSize: 16,
                  color: isDark ? Colors.grey.shade400 : Colors.grey,
                ),
              ),
            ],
          ),
        );
      }
      return Center(
        child: Text(
          'Ничего не найдено',
          style: TextStyle(
            color: isDark ? Colors.grey.shade400 : Colors.grey,
          ),
        ),
      );
    }

    return ListView.builder(
      itemCount: _products.length,
      itemBuilder: (context, index) {
        final p = _products[index];
        final part = p['part_number'] ?? '';
        final model = p['model_number'] ?? '';
        final desc = p['description'] ?? '';
        final weight = p['weight'];
        final category = p['category']?['name'];
        final colorRus = p['color']?['rus'];
        final isActive = p['is_active'] ?? true;

        return Card(
          margin: const EdgeInsets.only(bottom: 8),
          child: InkWell(
            onTap: () => _openProduct(p['id']),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          part,
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                      ),
                      if (!isActive)
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: Colors.red.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text(
                            'удалён',
                            style: TextStyle(fontSize: 10, color: Colors.red),
                          ),
                        ),
                    ],
                  ),
                  if (model.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      model,
                      style: TextStyle(
                        fontSize: 13,
                        color: isDark ? Colors.blue.shade300 : Colors.blue.shade700,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                  if (desc.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      desc,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: isDark ? Colors.grey.shade300 : Colors.grey[700],
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      if (weight != null)
                        _chip(
                          '⚖️ ${weight.toString()} кг',
                          Colors.orange,
                          isDark,
                        ),
                      if (category != null)
                        _chip(category, Colors.purple, isDark),
                      if (category == null)
                        _chip('нет категории', Colors.red, isDark),
                      if (colorRus != null)
                        _chip(colorRus, Colors.teal, isDark),
                    ],
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  /// Универсальная «плашка» — работает в обеих темах.
  Widget _chip(String text, MaterialColor color, bool isDark) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: isDark ? color.withOpacity(0.15) : color.shade50,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          color: isDark ? color.shade200 : color.shade700,
        ),
      ),
    );
  }
}