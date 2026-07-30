# Product Fetcher (Local Flask Server)

Ek local tool jo Chrome mein khulta hai — left side URL box, right side result panel.

## Setup (ek baar)

```bash
cd meesho-scraper
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

## Chalane ke liye

```bash
python app.py
```

Terminal mein `http://127.0.0.1:5000` dikhega — usko Chrome mein khol lo.

## Use kaise karein

1. Left box mein product page ka URL daalo (e.g. Meesho product page link)
2. **Fetch** button dabao
3. Right panel mein data A-to-Z dikh jaayega:
   - Product name, image, canonical URL
   - Meta description se nikaale gaye saare fields (Brand, Capacity, etc.)
   - Category breadcrumbs
   - Raw JSON-LD (debug/expansion ke liye, neeche collapsed rehta hai)

## Kaam kaise karta hai

- `app.py` — Flask server, ek hi route `/api/fetch` hai jo URL leke scraper ko call karta hai.
- `scraper.py` — saari scraping logic yahan hai (modular rakha hai taaki naye function add karna easy ho).
- `templates/index.html`, `static/` — UI (left panel + right panel).

Ye `requests` + `BeautifulSoup` use karta hai (raw HTML fetch), jo Meesho jaisi
sites pe kaafi data de deta hai kyunki SEO ke liye product info meta tags aur
JSON-LD mein server-side hi render hoti hai. Agar koi page fully JS ke baad
hi data dikhata hai (jaise live price ya pincode-wise delivery estimate),
uske liye alag se ek Selenium/Playwright-based module add karna padega —
abhi ka structure usko easily accommodate kar sakta hai.

## Naya module add karna ho (jaise pincode delivery check)

1. `scraper.py` mein naya function likho (jo requests/Selenium se woh specific
   data nikaale).
2. `app.py` mein naya route bana ke usko call karo, jaise `/api/pincode-check`.
3. `static/script.js` aur `index.html` mein ek naya input/button add karke
   us naye route ko hit karo.

Isi tarah left panel pe aur functions/buttons add hote jaayenge, aur right
panel un sabka output dikhata rahega.
