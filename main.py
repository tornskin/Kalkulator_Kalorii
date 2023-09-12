from flask import Flask, render_template, request, flash, redirect
from flask_sqlalchemy import SQLAlchemy
import datetime
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Zmień na własny klucz
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meals.db'
db = SQLAlchemy(app)

class Meal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    carbohydrates = db.Column(db.Float, nullable=False)
    fat = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=datetime.datetime.now().date())
    grams = db.Column(db.Float, nullable=False, default=100)  # Domyślnie 100 gramów

def search_food(query):
    api_url = 'https://world.openfoodfacts.org/cgi/search.pl'
    params = {
        'search_terms': query,
        'search_simple': '1',
        'json': '1',
    }
    try:
        response = requests.get(api_url, params=params)
        response.raise_for_status()  # Podnosi błąd, jeśli status odpowiedzi nie jest 200 OK
        data = response.json()
        products = data.get('products', [])

        results = []
        for product in products:
            name = product.get('product_name', '')
            calories = float(product.get('nutriments', {}).get('energy-kcal_100g', 0))
            protein = float(product.get('nutriments', {}).get('proteins_100g', 0))
            carbohydrates = float(product.get('nutriments', {}).get('carbohydrates_100g', 0))
            fat = float(product.get('nutriments', {}).get('fat_100g', 0))

            results.append({
                'name': name,
                'calories': calories,
                'protein': protein,
                'carbohydrates': carbohydrates,
                'fat': fat,
            })

        return results
    except requests.exceptions.RequestException as e:
        print(f'Wystąpił błąd podczas komunikacji z API: {e}')
        return []

@app.route('/')
def index():
    meals = db.session.query(Meal).filter(Meal.date == datetime.datetime.now().date()).all()
    return render_template('index.html', meals=meals)

@app.route('/search')
def search():
    query = request.args.get('query', '')
    search_results = search_food(query)
    return render_template('search_results.html', query=query, search_results=search_results)


@app.route('/add_meal', methods=['POST'])
def add_meal():
    selected_product = request.form.get('selected_product')
    selected_product_name, selected_product_index = selected_product.split('_')

    # Pobierz dane produktu z formularza
    name = request.form.get(f'search_results[{selected_product_index}][0]')
    calories = float(request.form.get(f'search_results[{selected_product_index}][1]'))
    protein = float(request.form.get(f'search_results[{selected_product_index}][2]'))
    carbohydrates = float(request.form.get(f'search_results[{selected_product_index}][3]'))
    fat = float(request.form.get(f'search_results[{selected_product_index}][4]'))

    if selected_product_name:
        if selected_product_index is not None:
            grams = 100  # Domyślnie 100 gramów

            new_meal = Meal(
                name=name,
                calories=calories * (grams / 100),
                protein=protein * (grams / 100),
                carbohydrates=carbohydrates * (grams / 100),
                fat=fat * (grams / 100)
            )
            db.session.add(new_meal)
            db.session.commit()
            flash('Posiłek został dodany!')
        else:
            flash('Błąd: Brak indeksu produktu.')
    else:
        flash('Błąd: Wybierz produkt do dodania.')

    return redirect('/')


@app.route('/edit_meal/<int:meal_id>', methods=['GET', 'POST'])
def edit_meal(meal_id):
    meal = Meal.query.get(meal_id)

    if not meal:
        flash('Posiłek nie istnieje.')
        return redirect('/')

    if request.method == 'POST':
        grams = float(request.form.get('grams'))

        if grams <= 0:
            flash('Ilość gram musi być dodatnia.')
        else:
            # Przelicz składniki odżywcze na nową ilość gram
            multiplier = grams / meal.grams
            meal.grams = grams
            meal.calories *= multiplier
            meal.protein *= multiplier
            meal.carbohydrates *= multiplier
            meal.fat *= multiplier
            db.session.commit()
            flash('Posiłek został zaktualizowany.')
        return redirect('/')

    return render_template('edit_meal.html', meal=meal)


@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
def delete_meal(meal_id):
    meal = Meal.query.get(meal_id)

    if not meal:
        flash('Posiłek nie istnieje.')
    else:
        db.session.delete(meal)
        db.session.commit()
        flash('Posiłek został usunięty.')

    return redirect('/')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)