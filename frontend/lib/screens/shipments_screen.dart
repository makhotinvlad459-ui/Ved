// frontend/lib/screens/shipments_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import 'shipment_detail_screen.dart';

class ShipmentsScreen extends StatefulWidget {
  const ShipmentsScreen({super.key});

  @override
  State<ShipmentsScreen> createState() => _ShipmentsScreenState();
}

class _ShipmentsScreenState extends State<ShipmentsScreen> {
  List<dynamic> _shipments = [];
  bool _isLoading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _loadShipments();
  }

  Future<void> _loadShipments() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final data = await api.getShipments();
      setState(() {
        _shipments = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Ошибка загрузки: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _createShipment() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (context) => _CreateShipmentDialog(),
    );

    if (result != null) {
      try {
        final api = Provider.of<ApiService>(context, listen: false);
        await api.createShipment(
          shipmentNumber: result['shipment_number']!,
          invoiceNumber: result['invoice_number'],
          supplier: result['supplier'],
        );
        await _loadShipments();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('✅ Поставка создана!'),
            backgroundColor: Colors.green,
          ),
        );
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('❌ Ошибка: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('📦 Поставки'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: _createShipment,
          ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _loadShipments,
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error.isNotEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error, color: Colors.red, size: 48),
                        const SizedBox(height: 16),
                        Text(_error),
                        ElevatedButton(
                          onPressed: _loadShipments,
                          child: const Text('Повторить'),
                        ),
                      ],
                    ),
                  )
                : _shipments.isEmpty
                    ? const Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.inbox, color: Colors.grey, size: 48),
                            SizedBox(height: 16),
                            Text(
                              'Нет поставок',
                              style: TextStyle(color: Colors.grey),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        itemCount: _shipments.length,
                        itemBuilder: (context, index) {
                          final s = _shipments[index];
                          return _ShipmentCard(
                            shipment: s,
                            onTap: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(
                                  builder: (context) => ShipmentDetailScreen(
                                    shipmentId: s['id'],
                                  ),
                                ),
                              ).then((_) => _loadShipments());
                            },
                            onDelete: () async {
                              final confirm = await showDialog<bool>(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: const Text('Удалить поставку?'),
                                  content: Text(
                                      'Вы уверены, что хотите удалить поставку ${s['shipment_number']}?'),
                                  actions: [
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(context, false),
                                      child: const Text('Отмена'),
                                    ),
                                    TextButton(
                                      onPressed: () =>
                                          Navigator.pop(context, true),
                                      child: const Text(
                                        'Удалить',
                                        style: TextStyle(color: Colors.red),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                              if (confirm == true) {
                                try {
                                  final api = Provider.of<ApiService>(context,
                                      listen: false);
                                  await api.deleteShipment(s['id']);
                                  await _loadShipments();
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text('🗑️ Поставка удалена'),
                                      backgroundColor: Colors.grey,
                                    ),
                                  );
                                } catch (e) {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('❌ Ошибка: $e'),
                                      backgroundColor: Colors.red,
                                    ),
                                  );
                                }
                              }
                            },
                          );
                        },
                      ),
      ),
    );
  }
}

// ========== КАРТОЧКА ПОСТАВКИ ==========
class _ShipmentCard extends StatelessWidget {
  final dynamic shipment;
  final VoidCallback onTap;
  final VoidCallback onDelete;

  const _ShipmentCard({
    required this.shipment,
    required this.onTap,
    required this.onDelete,
  });

  String _getStatusText(String status) {
    switch (status) {
      case 'completed':
        return '✅ Завершена';
      case 'cancelled':
        return '❌ Отменена';
      default:
        return '🔄 В процессе';
    }
  }

  Color _getProgressColor(int progress) {
    if (progress >= 80) return Colors.green;
    if (progress >= 50) return Colors.orange;
    return Colors.blue;
  }

  @override
  Widget build(BuildContext context) {
    final progress = shipment['progress'] ?? 0;
    final status = shipment['status'] ?? 'in_progress';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          shipment['shipment_number'] ?? '',
                          style: const TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: status == 'completed'
                                ? Colors.green.withOpacity(0.1)
                                : Colors.orange.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Text(
                            _getStatusText(status),
                            style: TextStyle(
                              fontSize: 11,
                              color: status == 'completed'
                                  ? Colors.green
                                  : Colors.orange,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      shipment['invoice_number'] ?? 'Без инвойса',
                      style: TextStyle(
                        fontSize: 14,
                        color: Colors.grey[600],
                      ),
                    ),
                    if (shipment['supplier'] != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        shipment['supplier'],
                        style: TextStyle(
                          fontSize: 13,
                          color: Colors.grey[500],
                        ),
                      ),
                    ],
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(4),
                            child: LinearProgressIndicator(
                              value: progress / 100,
                              backgroundColor: Colors.grey[200],
                              color: _getProgressColor(progress),
                              minHeight: 6,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Text(
                          '$progress%',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                            color: _getProgressColor(progress),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                icon: const Icon(Icons.delete_outline, color: Colors.grey),
                onPressed: onDelete,
                tooltip: 'Удалить',
              ),
              const Icon(Icons.chevron_right, color: Colors.grey),
            ],
          ),
        ),
      ),
    );
  }
}

// ========== ДИАЛОГ СОЗДАНИЯ ПОСТАВКИ ==========
class _CreateShipmentDialog extends StatefulWidget {
  const _CreateShipmentDialog();

  @override
  State<_CreateShipmentDialog> createState() => __CreateShipmentDialogState();
}

class __CreateShipmentDialogState extends State<_CreateShipmentDialog> {
  final _formKey = GlobalKey<FormState>();
  final _numberController = TextEditingController();
  final _invoiceController = TextEditingController();
  final _supplierController = TextEditingController();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('📦 Новая поставка'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextFormField(
              controller: _numberController,
              decoration: const InputDecoration(
                labelText: 'Номер поставки',
                hintText: 'Поставка №1',
              ),
              validator: (value) =>
                  value?.isEmpty == true ? 'Введите номер' : null,
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _invoiceController,
              decoration: const InputDecoration(
                labelText: 'Номер инвойса (опционально)',
                hintText: 'K466',
              ),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _supplierController,
              decoration: const InputDecoration(
                labelText: 'Поставщик (опционально)',
                hintText: 'KVN Group FZCO',
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Отмена'),
        ),
        ElevatedButton(
          onPressed: () {
            if (_formKey.currentState?.validate() ?? false) {
              Navigator.pop(context, {
                'shipment_number': _numberController.text,
                'invoice_number': _invoiceController.text.isEmpty
                    ? null
                    : _invoiceController.text,
                'supplier': _supplierController.text.isEmpty
                    ? null
                    : _supplierController.text,
              });
            }
          },
          style: ElevatedButton.styleFrom(
            backgroundColor: Colors.blue,
            foregroundColor: Colors.white,
          ),
          child: const Text('Создать'),
        ),
      ],
    );
  }
}