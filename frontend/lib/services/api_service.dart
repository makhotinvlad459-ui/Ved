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

  // ============================================================
  // 1. СПЕЦИФИКАЦИЯ
  // ============================================================

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

  Future<Map<String, dynamic>> getStatus(String sessionId) async {
    try {
      final response = await _dio.get('/upload/status/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения статуса: $e');
    }
  }

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

  // ============================================================
  // 2. PENDING MODELS
  // ============================================================

  Future<List<dynamic>> getPendingModels(String sessionId) async {
    try {
      final response = await _dio.get('/models/pending/$sessionId');
      return response.data['new_models'] ?? [];
    } catch (e) {
      throw Exception('Ошибка получения новых моделей: $e');
    }
  }

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

  // ============================================================
  // 3. КАТЕГОРИИ И ЦВЕТА
  // ============================================================

  Future<List<dynamic>> getCategories() async {
    try {
      final response = await _dio.get('/categories/');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения категорий: $e');
    }
  }

  Future<List<dynamic>> getColors() async {
    try {
      final response = await _dio.get('/colors/');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения цветов: $e');
    }
  }

  Future<Map<String, dynamic>> getCategoriesAndColors() async {
    try {
      final categories = await getCategories();
      final colors = await getColors();
      return {'categories': categories, 'colors': colors};
    } catch (e) {
      throw Exception('Ошибка получения категорий и цветов: $e');
    }
  }

  Future<Map<String, dynamic>> getCategory(int id) async {
    try {
      final response = await _dio.get('/categories/$id');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения категории: $e');
    }
  }

  Future<Map<String, dynamic>> createFullCategory({
    required String name,
    String? nameEng,
    required String prefixRu,
    String? prefixEng,
    bool collectSerials = true,
    String serialSource = 'serial_number',
    bool cleanSerialPrefix = true,
  }) async {
    try {
      final response = await _dio.post('/categories/', data: {
        'name': name,
        'name_eng': nameEng,
        'prefix_ru': prefixRu,
        'prefix_eng': prefixEng,
        'collect_serials': collectSerials,
        'serial_source': serialSource,
        'clean_serial_prefix': cleanSerialPrefix,
      });
      return response.data;
    } catch (e) {
      throw Exception('Ошибка создания категории: $e');
    }
  }

  Future<Map<String, dynamic>> createCategory({
    required String name,
    required String prefixRu,
    String? nameEng,
  }) async {
    return createFullCategory(
      name: name,
      nameEng: nameEng,
      prefixRu: prefixRu,
    );
  }

  Future<Map<String, dynamic>> updateCategory({
    required int id,
    String? name,
    String? nameEng,
    String? prefixRu,
    String? prefixEng,
    bool? collectSerials,
    String? serialSource,
    bool? cleanSerialPrefix,
    bool? isActive,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (name != null) body['name'] = name;
      if (nameEng != null) body['name_eng'] = nameEng;
      if (prefixRu != null) body['prefix_ru'] = prefixRu;
      if (prefixEng != null) body['prefix_eng'] = prefixEng;
      if (collectSerials != null) body['collect_serials'] = collectSerials;
      if (serialSource != null) body['serial_source'] = serialSource;
      if (cleanSerialPrefix != null) body['clean_serial_prefix'] = cleanSerialPrefix;
      if (isActive != null) body['is_active'] = isActive;

      final response = await _dio.put('/categories/$id', data: body);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка обновления категории: $e');
    }
  }

  Future<Map<String, dynamic>> createColor({
    required String eng,
    required String rus,
  }) async {
    try {
      final response = await _dio.post('/colors/', data: {
        'eng': eng,
        'rus': rus,
      });
      return response.data;
    } catch (e) {
      throw Exception('Ошибка создания цвета: $e');
    }
  }

  // ============================================================
  // 4. ТОВАРЫ (Products)
  // ============================================================

  Future<Map<String, dynamic>> searchProducts(
  String query, {
  bool missingCategory = false,
}) async {
  try {
    final response = await _dio.get(
      '/models/search',
      queryParameters: {
        if (query.trim().isNotEmpty) 'q': query.trim(),
        if (missingCategory) 'missing_category': true,
        'limit': 500,
      },
    );
    return response.data;
  } catch (e) {
    throw Exception('Ошибка поиска: $e');
  }
}

  Future<Map<String, dynamic>> getProduct(int id) async {
    try {
      final response = await _dio.get('/models/$id');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения товара: $e');
    }
  }

  Future<Map<String, dynamic>> createProduct({
    required String partNumber,
    required String modelNumber,
    String? description,
    String? coo,
    String? upc,
    double? weight,
    int? categoryId,
    int? colorId,
    String? customNameRu,
  }) async {
    try {
      final body = <String, dynamic>{
        'part_number': partNumber,
        'model_number': modelNumber,
        'is_active': true,
      };
      if (description != null) body['description'] = description;
      if (coo != null) body['coo'] = coo;
      if (upc != null) body['upc'] = upc;
      if (weight != null) body['weight'] = weight;
      if (categoryId != null) body['category_id'] = categoryId;
      if (colorId != null) body['color_id'] = colorId;
      if (customNameRu != null) body['custom_name_ru'] = customNameRu;

      final response = await _dio.post('/models/', data: body);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка создания товара: $e');
    }
  }

  Future<Map<String, dynamic>> updateProduct({
    required int id,
    String? partNumber,
    String? modelNumber,
    String? description,
    String? coo,
    String? upc,
    double? weight,
    int? categoryId,
    int? colorId,
    String? customNameRu,
    bool? isActive,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (partNumber != null) body['part_number'] = partNumber;
      if (modelNumber != null) body['model_number'] = modelNumber;
      if (description != null) body['description'] = description;
      if (coo != null) body['coo'] = coo;
      if (upc != null) body['upc'] = upc;
      body['weight'] = weight;
      body['category_id'] = categoryId;
      body['color_id'] = colorId;
      if (customNameRu != null) body['custom_name_ru'] = customNameRu;
      if (isActive != null) body['is_active'] = isActive;

      final response = await _dio.put('/models/$id', data: body);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка обновления товара: $e');
    }
  }

  Future<void> deleteProduct(int id) async {
    try {
      await _dio.delete('/models/$id');
    } catch (e) {
      throw Exception('Ошибка удаления товара: $e');
    }
  }

  // ============================================================
  // 5. PACKING LIST
  // ============================================================

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

  Future<Map<String, dynamic>> getPackingListStatus(String sessionId) async {
    try {
      final response = await _dio.get('/packing-list/status/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения статуса: $e');
    }
  }

  Future<Map<String, dynamic>> getPendingWeights(String sessionId) async {
    try {
      final response = await _dio.get('/packing-list/pending/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения pending весов: $e');
    }
  }

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

  // ============================================================
  // 6. ЧЕСТНЫЙ ЗНАК — в спецификацию
  // ============================================================

  Future<Map<String, dynamic>> uploadCzFiles({
    required List<int> invoiceBytes,
    required String invoiceName,
    required List<int> specBytes,
    required String specName,
    required List<int> czBytes,
    required String czName,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'invoice': MultipartFile.fromBytes(invoiceBytes, filename: invoiceName),
        'specification': MultipartFile.fromBytes(specBytes, filename: specName),
        'cz_file': MultipartFile.fromBytes(czBytes, filename: czName),
      });
      final response = await _dio.post('/chestny-znak/upload', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки: $e');
    }
  }

  Future<Map<String, dynamic>> getCzStatus(String sessionId) async {
    try {
      final response = await _dio.get('/chestny-znak/status/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения статуса: $e');
    }
  }

  Future<Response> downloadCzResult(String sessionId) async {
    try {
      return await _dio.get(
        '/chestny-znak/download/$sessionId',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw Exception('Ошибка скачивания: $e');
    }
  }

  // ============================================================
  // 7. КОММЕРЧЕСКОЕ ПРЕДЛОЖЕНИЕ
  // ============================================================

  Future<Map<String, dynamic>> uploadCommercialOffer({
    required List<int> specBytes,
    required String specName,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'specification': MultipartFile.fromBytes(specBytes, filename: specName),
      });
      final response =
          await _dio.post('/commercial-offer/upload', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки: $e');
    }
  }

  Future<Map<String, dynamic>> getCommercialOfferStatus(
      String sessionId) async {
    try {
      final response = await _dio.get('/commercial-offer/status/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения статуса: $e');
    }
  }

  Future<Response> downloadCommercialOffer(String sessionId) async {
    try {
      return await _dio.get(
        '/commercial-offer/download/$sessionId',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw Exception('Ошибка скачивания: $e');
    }
  }

  // ============================================================
  // 8. КОДЫ ЧЗ ДЛЯ ВВОДА
  // ============================================================

  Future<Map<String, dynamic>> uploadCzCodes({
    required List<int> czSpecBytes,
    required String czSpecName,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'cz_spec': MultipartFile.fromBytes(czSpecBytes, filename: czSpecName),
      });
      final response = await _dio.post('/cz-codes/upload', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки: $e');
    }
  }

  Future<Map<String, dynamic>> getCzCodesStatus(String sessionId) async {
    try {
      final response = await _dio.get('/cz-codes/status/$sessionId');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка получения статуса: $e');
    }
  }

  Future<Response> downloadCzCodes(String sessionId) async {
    try {
      return await _dio.get(
        '/cz-codes/download/$sessionId',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw Exception('Ошибка скачивания: $e');
    }
  }

  // ============================================================
  // 9. КАРТОЧКИ ЧЗ (K3)
  // ============================================================

  Future<Map<String, dynamic>> parseCzInvoice({
    required List<int> bytes,
    required String fileName,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'invoice': MultipartFile.fromBytes(bytes, filename: fileName),
      });
      final response = await _dio.post('/cz/cards/parse-invoice', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка парсинга: $e');
    }
  }

  Future<Map<String, dynamic>> generateCzCards({
    required String sessionId,
    required List<String> partNumbers,
  }) async {
    try {
      final response = await _dio.post(
        '/cz/cards/generate',
        data: {
          'session_id': sessionId,
          'part_numbers': partNumbers,
        },
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка генерации: $e');
    }
  }

  Future<Response> downloadCzCards(String sessionId) async {
    try {
      return await _dio.get(
        '/cz/cards/download/$sessionId',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw Exception('Ошибка скачивания: $e');
    }
  }

  // ============================================================
  // 10. СПРАВОЧНИК ЧЗ — МОДЕЛИ
  // ============================================================

  Future<List<dynamic>> getCzCardProducts({String query = ''}) async {
    try {
      final response = await _dio.get(
        '/cz/card-products',
        queryParameters: {
          if (query.trim().isNotEmpty) 'q': query.trim(),
          'limit': 500,
        },
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки моделей: $e');
    }
  }

  Future<Map<String, dynamic>> getCzCardProduct(int id) async {
    try {
      final response = await _dio.get('/cz/card-products/$id');
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки модели: $e');
    }
  }

  Future<Map<String, dynamic>> createCzCardProduct({
    required String modelName,
    required String brand,
    double? screenSize,
    int? ramGb,
    String? cpuVendor,
    String? cpuModel,
  }) async {
    try {
      final response = await _dio.post('/cz/card-products', data: {
        'model_name': modelName,
        'brand': brand,
        'screen_size': screenSize,
        'ram_gb': ramGb,
        'cpu_vendor': cpuVendor,
        'cpu_model': cpuModel,
        'is_estimated': false,
      });
      return response.data;
    } catch (e) {
      throw Exception('Ошибка создания модели: $e');
    }
  }

  Future<Map<String, dynamic>> updateCzCardProduct({
    required int id,
    String? modelName,
    String? brand,
    double? screenSize,
    int? ramGb,
    String? cpuVendor,
    String? cpuModel,
    bool? isActive,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (modelName != null) body['model_name'] = modelName;
      if (brand != null) body['brand'] = brand;
      body['screen_size'] = screenSize;
      body['ram_gb'] = ramGb;
      body['cpu_vendor'] = cpuVendor;
      body['cpu_model'] = cpuModel;
      if (isActive != null) body['is_active'] = isActive;

      final response = await _dio.put('/cz/card-products/$id', data: body);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка обновления модели: $e');
    }
  }

  Future<void> deleteCzCardProduct(int id) async {
    try {
      await _dio.delete('/cz/card-products/$id');
    } catch (e) {
      throw Exception('Ошибка удаления модели: $e');
    }
  }

  // ============================================================
  // 11. СПРАВОЧНИК ЧЗ — ЦВЕТА
  // ============================================================

  Future<List<dynamic>> getCzColorMappings({String query = ''}) async {
    try {
      final response = await _dio.get(
        '/cz/color-mappings',
        queryParameters: {
          if (query.trim().isNotEmpty) 'q': query.trim(),
        },
      );
      return response.data;
    } catch (e) {
      throw Exception('Ошибка загрузки цветов: $e');
    }
  }

  Future<Map<String, dynamic>> createCzColorMapping({
    required String eng,
    required String czValue,
  }) async {
    try {
      final response = await _dio.post('/cz/color-mappings', data: {
        'eng': eng,
        'cz_value': czValue,
      });
      return response.data;
    } catch (e) {
      throw Exception('Ошибка создания цвета: $e');
    }
  }

  Future<Map<String, dynamic>> updateCzColorMapping({
    required int id,
    String? eng,
    String? czValue,
    bool? isActive,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (eng != null) body['eng'] = eng;
      if (czValue != null) body['cz_value'] = czValue;
      if (isActive != null) body['is_active'] = isActive;

      final response = await _dio.put('/cz/color-mappings/$id', data: body);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка обновления цвета: $e');
    }
  }

  Future<void> deleteCzColorMapping(int id) async {
    try {
      await _dio.delete('/cz/color-mappings/$id');
    } catch (e) {
      throw Exception('Ошибка удаления цвета: $e');
    }
  }

    // ============================================================
  // FOR ALICE
  // ============================================================

  Future<Map<String, dynamic>> forAliceProcess({
    required List<Map<String, dynamic>> items,
    required double logisticsRateUsd,
    required double usdToAed,
    required double documentsCostAed,
  }) async {
    try {
      final response = await _dio.post('/for-alice/process', data: {
        'items': items,
        'logistics_rate_usd': logisticsRateUsd,
        'usd_to_aed': usdToAed,
        'documents_cost_aed': documentsCostAed,
      });
      return response.data;
    } catch (e) {
      throw Exception('Ошибка расчёта: $e');
    }
  }

  Future<Map<String, dynamic>> forAliceGenerate({
    required List<Map<String, dynamic>> items,
    required double logisticsRateUsd,
    required double usdToAed,
    required double documentsCostAed,
  }) async {
    try {
      final response = await _dio.post('/for-alice/generate', data: {
        'items': items,
        'logistics_rate_usd': logisticsRateUsd,
        'usd_to_aed': usdToAed,
        'documents_cost_aed': documentsCostAed,
      });
      return response.data;
    } catch (e) {
      throw Exception('Ошибка генерации: $e');
    }
  }

  Future<Map<String, dynamic>> forAliceSaveWeight({
    required String partNumber,
    required double weight,
    String? name,
  }) async {
    try {
      final body = <String, dynamic>{
        'part_number': partNumber,
        'weight': weight,
      };
      if (name != null && name.isNotEmpty) {
        body['name'] = name;
      }
      final response = await _dio.post('/for-alice/save-weight', data: body);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка сохранения веса: $e');
    }
  }

  Future<Response> forAliceDownload(String sessionId) async {
    try {
      return await _dio.get(
        '/for-alice/download/$sessionId',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw Exception('Ошибка скачивания: $e');
    }
  }

      // ============================================================
  // 12. ДЕКЛАРИРОВАНИЕ (ОДИН ИНВОЙС)
  // ============================================================

  Future<Map<String, dynamic>> getDeclarationText({
    required List<int> bytes,
    required String fileName,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'invoice': MultipartFile.fromBytes(bytes, filename: fileName),
      });
      final response = await _dio.post('/upload/declaration-text', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка генерации текста: $e');
    }
  }
    // ============================================================
  // 13. FAR EAST (ТАМОЖНЯ)
  // ============================================================

  Future<Map<String, dynamic>> getFarEastText({
    required List<int> bytes,
    required String fileName,
  }) async {
    try {
      FormData formData = FormData.fromMap({
        'file': MultipartFile.fromBytes(bytes, filename: fileName),
      });
      final response = await _dio.post('/upload/far-east-text', data: formData);
      return response.data;
    } catch (e) {
      throw Exception('Ошибка генерации текста Far East: $e');
    }
  }
}