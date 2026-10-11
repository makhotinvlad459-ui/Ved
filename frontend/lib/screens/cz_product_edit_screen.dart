// frontend/lib/screens/cz_product_edit_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

class CzProductEditScreen extends StatefulWidget {
  final int? productId;

  const CzProductEditScreen({super.key, this.productId});

  @override
  State<CzProductEditScreen> createState() => _CzProductEditScreenState();
}

class _CzProductEditScreenState extends State<CzProductEditScreen> {
  bool _isLoading = true;
  bool _isSaving = false;
  String _error = '';
  bool _isNew = false;

  final _modelNameController = TextEditingController();
  final _brandController = TextEditingController();
  final _screenController = TextEditingController();
  final _ramController = TextEditingController();
  final _cpuVendorController = TextEditingController();
  final _cpuModelController = TextEditingController();
  bool _isActive = true;

  @override
  void initState() {
    super.initState();
    _isNew = widget.productId == null;
    if (_isNew) {
      _isLoading = false;
    } else {
      _load();
    }
  }

  @override
  void dispose() {
    _modelNameController.dispose();
    _brandController.dispose();
    _screenController.dispose();
    _ramController.dispose();
    _cpuVendorController.dispose();
    _cpuModelController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final p = await api.getCzCardProduct(widget.productId!);

      if (!mounted) return;
      setState(() {
        _modelNameController.text = p['model_name'] ?? '';
        _brandController.text = p['brand'] ?? '';
        _screenController.text = p['screen_size']?.toString() ?? '';
        _ramController.text = p['ram_gb']?.toString() ?? '';
        _cpuVendorController.text = p['cpu_vendor'] ?? '';
        _cpuModelController.text = p['cpu_model'] ?? '';
        _isActive = p['is_active'] ?? true;
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
    final modelName = _modelNameController.text.trim();
    final brand = _brandController.text.trim();

    if (modelName.isEmpty || brand.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Заполните модель и бренд'),
          backgroundColor: Colors.red,
        ),
      );
      return;
    }

    setState(() => _isSaving = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);

      final screenSize = _screenController.text.trim().isEmpty
          ? null
          : double.tryParse(_screenController.text.trim());
      final ramGb = _ramController.text.trim().isEmpty
          ? null
          : int.tryParse(_ramController.text.trim());

      if (_isNew) {
        await api.createCzCardProduct(
          modelName: modelName,
          brand: brand,
          screenSize: screenSize,
          ramGb: ramGb,
          cpuVendor: _cpuVendorController.text.trim().isEmpty
              ? null
              : _cpuVendorController.text.trim(),
          cpuModel: _cpuModelController.text.trim().isEmpty
              ? null
              : _cpuModelController.text.trim(),
        );
      } else {
        await api.updateCzCardProduct(
          id: widget.productId!,
          modelName: modelName,
          brand: brand,
          screenSize: screenSize,
          ramGb: ramGb,
          cpuVendor: _cpuVendorController.text.trim().isEmpty
              ? null
              : _cpuVendorController.text.trim(),
          cpuModel: _cpuModelController.text.trim().isEmpty
              ? null
              : _cpuModelController.text.trim(),
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
        title: const Text('Удалить модель?'),
        content: Text('Модель «${_modelNameController.text}» будет скрыта из справочника.'),
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
      await api.deleteCzCardProduct(widget.productId!);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('🗑️ Модель удалена'),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_isNew ? 'Новая модель' : 'Модель'),
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
                  child: Text(_error, style: const TextStyle(color: Colors.red)),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    TextField(
                      controller: _modelNameController,
                      decoration: const InputDecoration(
                        labelText: 'Модель *',
                        hintText: 'Например: iPhone 19 Pro',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),

                    TextField(
                      controller: _brandController,
                      decoration: const InputDecoration(
                        labelText: 'Бренд *',
                        hintText: 'APPLE / Samsung',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _screenController,
                            keyboardType: const TextInputType.numberWithOptions(decimal: true),
                            decoration: const InputDecoration(
                              labelText: 'Экран, дюйм',
                              hintText: '6.3',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _ramController,
                            keyboardType: TextInputType.number,
                            decoration: const InputDecoration(
                              labelText: 'RAM, Гб',
                              hintText: '12',
                              border: OutlineInputBorder(),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),

                    TextField(
                      controller: _cpuVendorController,
                      decoration: const InputDecoration(
                        labelText: 'Производитель CPU',
                        hintText: 'Apple / Qualcomm / Samsung',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),

                    TextField(
                      controller: _cpuModelController,
                      decoration: const InputDecoration(
                        labelText: 'Модель CPU',
                        hintText: 'A20 Pro / Snapdragon 8 Elite Gen 5',
                        border: OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 16),

                    if (!_isNew)
                      SwitchListTile(
                        value: _isActive,
                        onChanged: (v) => setState(() => _isActive = v),
                        title: const Text('Активна'),
                        subtitle: const Text('Неактивные модели не участвуют в генерации'),
                        contentPadding: EdgeInsets.zero,
                      ),
                    const SizedBox(height: 16),

                    ElevatedButton(
                      onPressed: _isSaving ? null : _save,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.purple,
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