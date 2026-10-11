// frontend/lib/screens/cz_products_screen.dart
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';
import 'cz_product_edit_screen.dart';

class CzProductsScreen extends StatefulWidget {
  const CzProductsScreen({super.key});

  @override
  State<CzProductsScreen> createState() => _CzProductsScreenState();
}

class _CzProductsScreenState extends State<CzProductsScreen> {
  final TextEditingController _searchController = TextEditingController();
  Timer? _debounce;

  List<dynamic> _products = [];
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
      final data = await api.getCzCardProducts(query: query);
      if (!mounted) return;
      setState(() {
        _products = data;
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

  Future<void> _openProduct(int id) async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => CzProductEditScreen(productId: id),
      ),
    );
    if (result == true) _load(query: _searchController.text);
  }

  Future<void> _createNew() async {
    final result = await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => const CzProductEditScreen(productId: null),
      ),
    );
    if (result == true) _load(query: _searchController.text);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Модели ЧЗ'),
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
                hintText: 'Поиск: модель или бренд',
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
                    'Найдено: ${_products.length}',
                    style: const TextStyle(fontSize: 14, color: Colors.grey),
                  ),
                ),
                ElevatedButton.icon(
                  onPressed: _createNew,
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
    if (_products.isEmpty) {
      return const Center(
        child: Text('Ничего не найдено', style: TextStyle(color: Colors.grey)),
      );
    }

    return ListView.builder(
      itemCount: _products.length,
      itemBuilder: (context, index) {
        final p = _products[index];
        final modelName = p['model_name'] ?? '';
        final brand = p['brand'] ?? '';
        final screen = p['screen_size'];
        final ram = p['ram_gb'];
        final cpu = p['cpu_model'];
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
                          modelName,
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
                            color: Colors.red.shade50,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: const Text(
                            'удалён',
                            style: TextStyle(fontSize: 10, color: Colors.red),
                          ),
                        ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 4,
                    children: [
                      _chip(brand, Colors.blueGrey),
                      if (screen != null) _chip('${screen}"', Colors.blue),
                      if (ram != null) _chip('${ram} Гб', Colors.orange),
                      if (cpu != null) _chip(cpu, Colors.green),
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

  Widget _chip(String text, MaterialColor color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.shade50,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        text,
        style: TextStyle(fontSize: 12, color: color.shade700),
      ),
    );
  }
}