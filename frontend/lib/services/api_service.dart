// frontend/lib/services/api_service.dart
import 'package:dio/dio.dart';

class ApiService {
  static const String baseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
  final Dio _dio = Dio();

  ApiService() {
    _dio.options.baseUrl = baseUrl;
    _dio.options.connectTimeout = const Duration(seconds: 60);
    _dio.options.receiveTimeout = const Duration(seconds: 120);
  }

  // 1. Загрузка файлов (спецификация)
  Future<Map<String, dynamic>> uploadFiles({
    required List<int> invoiceBytes,
    required String invoiceName,
    required List<int> manifestBytes,
    required String manifestName,
    required List<int> templateBytes,
    required String templateName,
    String specNumber = '',
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'invoice': MultipartFile.fromBytes(invoiceBytes, filename: invoiceName),
        'manifest': MultipartFile.fromBytes(manifestBytes, filename: manifestName),
        'template': MultipartFile.fromBytes(templateBytes, filename: templateName),
        'spec_number': specNumber,
      });

      final response = await _dio.post('/upload/', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки: $e');
    }
  }

  // 2. Получение статуса
  Future<Map<String, dynamic>> getStatus(String sessionId) async {
    try {
      final response = await _dio.get('/upload/status/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения статуса: $e');
    }
  }

  // 3. Скачивание результата
  Future<Response> downloadResult(String sessionId) async {
    try {
      return await _dio.get(
        '/upload/download/$sessionId',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw Exception('Ошибка скачивания: $e');
    }
  }

  // 4. Получение списка новых моделей
  Future<List<dynamic>> getPendingModels(String sessionId) async {
    try {
      final response = await _dio.get('/models/pending/$sessionId');
      return response.data['new_models'] ?? [];
    } catch (e) {
      throw Exception('Ошибка получения новых моделей: $e');
    }
  }

  // 5. Подтверждение модели
  Future<Map<String, dynamic>> approveModel({
    required String sessionId,
    required int pendingId,
    String? customNameRu,
    int? customCategoryId,
    int? customColorId,
  }) async {
    try {
      final response = await _dio.post(
        '/models/pending/$sessionId/$pendingId/approve',
        data: {
          'custom_name_ru': customNameRu,
          'custom_category_id': customCategoryId,
          'custom_color_id': customColorId,
        },
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка подтверждения модели: $e');
    }
  }

  // 6. Подтверждение всех моделей
  Future<Map<String, dynamic>> approveAllModels(String sessionId) async {
    try {
      final response = await _dio.post(
        '/models/pending/$sessionId/approve-all',
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка подтверждения всех моделей: $e');
    }
  }

  // 7. Получение категорий
  Future<List<dynamic>> getCategories() async {
    try {
      final response = await _dio.get('/categories/');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения категорий: $e');
    }
  }

  // 8. Получение цветов
  Future<List<dynamic>> getColors() async {
    try {
      final response = await _dio.get('/colors/');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения цветов: $e');
    }
  }

  // 9. Получение всех категорий и цветов для выпадающих списков
  Future<Map<String, dynamic>> getCategoriesAndColors() async {
    try {
      final categories = await _dio.get('/categories/');
      final colors = await _dio.get('/colors/');
      return {
        'categories': categories.data,
        'colors': colors.data,
      };
    } catch (e) {
      throw Exception('Ошибка получения категорий и цветов: $e');
    }
  }

  // 10. Создание новой категории
  Future<Map<String, dynamic>> createCategory({
    required String name,
    required String prefixRu,
    String? nameEng,
  }) async {
    try {
      final response = await _dio.post(
        '/categories/',
        data: {
          'name': name,
          'name_eng': nameEng ?? name,
          'prefix_ru': prefixRu,
          'prefix_eng': '',
          'collect_serials': true,
          'serial_source': 'serial_number',
          'clean_serial_prefix': true,
        },
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка создания категории: $e');
    }
  }

  // 11. Создание нового цвета
  Future<Map<String, dynamic>> createColor({
    required String eng,
    required String rus,
  }) async {
    try {
      final response = await _dio.post(
        '/colors/',
        data: {
          'eng': eng,
          'rus': rus,
        },
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка создания цвета: $e');
    }
  }

  // 12. Загрузка Packing List
  Future<Map<String, dynamic>> uploadPackingList({
    required List<int> bytes,
    required String fileName,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(bytes, filename: fileName),
      });
      final response = await _dio.post('/packing-list/upload', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки: $e');
    }
  }

  // 13. Статус Packing List
  Future<Map<String, dynamic>> getPackingListStatus(String sessionId) async {
    try {
      final response = await _dio.get('/packing-list/status/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения статуса: $e');
    }
  }

  // 14. Получение pending весов
  Future<Map<String, dynamic>> getPendingWeights(String sessionId) async {
    try {
      final response = await _dio.get('/packing-list/pending/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения pending весов: $e');
    }
  }

  // 15. Подтверждение веса
  Future<Map<String, dynamic>> approveWeight(int pendingId, double weight) async {
    try {
      final response = await _dio.post(
        '/packing-list/pending/$pendingId/approve',
        queryParameters: {'weight': weight},
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка подтверждения веса: $e');
    }
  }

  // 16. Скачивание Packing List
  Future<Response> downloadPackingList(String sessionId) async {
    try {
      return await _dio.get(
        '/packing-list/download/$sessionId',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw Exception('Ошибка скачивания: $e');
    }
  }
}