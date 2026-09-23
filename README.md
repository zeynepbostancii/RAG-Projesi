# Bilge — RAG Tabanlı Kurumsal Doküman Asistanı

**Bilge**, farklı formatlardaki kurumsal dokümanlar üzerinde doğal dil ile arama yapılmasını sağlayan, **Retrieval-Augmented Generation (RAG)** mimarisi kullanılarak geliştirilmiş yerel bir yapay zekâ destekli doküman asistanıdır.

Proje, kullanıcıların dokümanlar hakkında doğal dilde sorular sormasını, ilgili içeriklerin bulunmasını ve cevapların hangi kaynaklara dayandığının görüntülenmesini amaçlamaktadır.

## 🚀 Özellikler

* 📄 PDF, Word, Excel, PowerPoint, TXT ve Markdown dosyalarını işleme
* 🌐 Web servislerinden alınan verileri RAG pipeline'ına dahil etme
* ✂️ Fixed-size ve Semantic Chunking
* 🧠 Multilingual embedding modeli ile metin vektörleştirme
* 🔎 Qdrant ile vektör tabanlı arama
* 🎯 Reranking ile arama sonuçlarının yeniden sıralanması
* 🔀 Hybrid Search yaklaşımı
* 🤖 Ollama üzerinden yerel LLM kullanımı
* 💬 Çok turlu konuşmalar için Query Rewriting
* 📚 Cevaplarda kaynak gösterimi
* 🔦 Kaynak metinlerde ilgili bölümlerin vurgulanması
* ⚡ Tekrarlanan sorgular için LRU Cache
* 📝 Doküman özetleme
* 🔄 Doküman karşılaştırma
* 🌙 Modern React arayüzü ve açık/koyu tema desteği

## 🏗️ Sistem Mimarisi

Projenin temel çalışma akışı:

```text
          ┌────────────────────┐
          │  PDF / Word / Excel│
          │ PPTX / TXT / Web   │
          └─────────┬──────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ Document Ingestion │
          │ & Text Extraction  │
          └─────────┬──────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ Chunking           │
          │ Fixed / Semantic   │
          └─────────┬──────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ Embedding Model    │
          │ MiniLM-L12-v2      │
          └─────────┬──────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ Qdrant Vector DB   │
          └─────────┬──────────┘
                    │
              User Question
                    │
                    ▼
          ┌────────────────────┐
          │ Retrieval          │
          │ + Reranking        │
          └─────────┬──────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ Local LLM          │
          │ Ollama / Qwen2.5   │
          └─────────┬──────────┘
                    │
                    ▼
          ┌────────────────────┐
          │ Answer + Sources   │
          └────────────────────┘
```

## 🧠 RAG Pipeline

Bilge'de dokümanlar öncelikle metin haline getirilir ve daha küçük parçalara ayrılır.

Embedding aşamasında:

```text
paraphrase-multilingual-MiniLM-L12-v2
```

modeli kullanılarak metinler **384 boyutlu embedding vektörlerine** dönüştürülür.

Bu vektörler Qdrant üzerinde saklanır. Kullanıcı bir soru sorduğunda ilgili içerikler önce vektör aramasıyla bulunur, ardından **BAAI/bge-reranker-base** kullanılarak aday sonuçlar yeniden sıralanır.

Son aşamada ilgili içerikler yerel LLM'e context olarak aktarılır ve cevap oluşturulur.

## 🤖 Kullanılan Yapay Zekâ Modelleri

### Embedding

* `paraphrase-multilingual-MiniLM-L12-v2`
* 384-dimensional embeddings
* Türkçe ve İngilizce içerikler için multilingual destek

### Reranker

* `BAAI/bge-reranker-base`

### Local LLM

* Ollama
* Qwen2.5 7B
* Qwen2.5 3B

Yerel LLM kullanımı sayesinde sistem, harici bir yapay zekâ servisine bağımlı olmadan çalışacak şekilde tasarlanmıştır.

## ⚙️ Teknolojiler

| Teknoloji             | Kullanım                |
| --------------------- | ----------------------- |
| Python                | Backend ve RAG pipeline |
| FastAPI               | REST API                |
| React                 | Frontend                |
| Qdrant                | Vector Database         |
| Ollama                | Local LLM               |
| Qwen2.5               | Metin üretimi           |
| Sentence Transformers | Embedding               |
| BGE Reranker          | Reranking               |
| PyPDF                 | PDF işleme              |
| python-docx           | Word işleme             |
| openpyxl              | Excel işleme            |
| python-pptx           | PowerPoint işleme       |

## 🔧 Kurulum

### 1. Repository'yi klonlayın

```bash
git clone https://github.com/USERNAME/REPOSITORY.git
cd REPOSITORY
```

### 2. Virtual Environment oluşturun

```bash
python -m venv venv
```

Windows:

```powershell
venv\Scripts\activate
```

### 3. Python bağımlılıklarını yükleyin

```bash
pip install -r requirements.txt
```

### 4. Ollama'yı çalıştırın

Gerekli modelin Ollama üzerinde bulunması gerekir.

Örneğin:

```bash
ollama pull qwen2.5:7b
```

veya

```bash
ollama pull qwen2.5:3b
```

### 5. FastAPI Backend'i başlatın

```bash
uvicorn api:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger dokümantasyonu:

```text
http://127.0.0.1:8000/docs
```

### 6. React arayüzünü başlatın

```bash
cd react-arayuz
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

## 💡 Kullanım

1. Bilge arayüzünü açın.
2. PDF, Word, Excel, PowerPoint veya desteklenen diğer dosyalardan birini yükleyin.
3. Sistem dokümanı işler ve vektör veritabanına kaydeder.
4. Doküman hakkında doğal dilde soru sorun.
5. Sistem ilgili içerikleri retrieval ve reranking aşamalarından geçirir.
6. Yerel LLM kullanılarak cevap oluşturulur.
7. Cevabın dayandığı kaynaklar kullanıcıya gösterilir.

## 🔍 Test ve Değerlendirme

Geliştirme sürecinde farklı senaryolar kullanılarak sistem test edilmiştir:

* Türkçe soru – İngilizce doküman
* Konuşmacı notlarında bulunan bilgiler
* Birden fazla dokümanda çelişen bilgiler
* Dokümanda bulunmayan bilgilerin sorulması
* Farklı dosya formatlarının birlikte kullanılması
* Retrieval sonuçlarının reranker öncesi ve sonrası karşılaştırılması

Bu testler ile yalnızca cevap üretimi değil, **retrieval kalitesi, model davranışı ve sistem performansı** ayrı ayrı değerlendirilmiştir.

## 📌 Bilinen Sınırlamalar

* Büyük dokümanlarda LLM tabanlı işlemler CPU üzerinde daha uzun sürebilir.
* Bazı sayısal ve tablo tabanlı sorgularda modelin yorumlama performansı sınırlı olabilir.
* Türkçe sorgular ile İngilizce dokümanlar arasındaki retrieval kalitesi sorguya göre değişebilir.
* Reranker, ilk retrieval aşamasında adaylara alınmayan bir içeriği sonradan değerlendiremez.

## 🎯 Projenin Amacı

Bu proje kapsamında amaç yalnızca çalışan bir chatbot oluşturmak değil; **dokümanların sisteme alınmasından bilgi retrieval sürecine, yeniden sıralamadan cevap üretimine ve kaynak gösterimine kadar uçtan uca bir RAG sistemi geliştirmektir.**

Proje aynı zamanda farklı RAG bileşenlerinin sistem performansına etkisini gözlemlemek ve sistemin güçlü/zayıf yönlerini test senaryoları üzerinden değerlendirmek amacıyla geliştirilmiştir.

## 👩‍💻 Geliştirici

**Zeynep Bostancı**
Computer Engineering Student
Karabük University

---

⭐ Bu proje, BTC Bilişim Hizmetleri A.Ş. bünyesinde gerçekleştirilen yazılım stajı kapsamında geliştirilmiştir.
