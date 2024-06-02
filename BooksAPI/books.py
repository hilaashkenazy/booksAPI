from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse
import requests
import uuid
from gemini import getAIsummary
from openlibrary import get_languages

BASE_URL = 'https://www.googleapis.com/books/v1/volumes'

app = Flask(__name__)
api = Api(app)

books = {}
ratings = {}


class Books(Resource):
    def get(self):
        """
               Retrieves books from the collection filtered based on query parameters.
               Supports filtering by various fields and special handling for 'language_contains' queries.
               """
        # Retrieve query parameters
        args = request.args
        filtered_books = list(books.values())

        # Handle special query for language
        if 'language' in args:
            lang = args['language']
            filtered_books = [book for book in filtered_books if lang in book.get('languages', [])]

        # Filter based on other field=value queries
        for key, value in args.items():
            if key not in ['summary', 'language']:
                filtered_books = [book for book in filtered_books if book.get(key) == value]

        return {'books': list(filtered_books)}, 200

    def post(self):
        """
                Creates a new book entry based on data provided via a POST request, fetching additional data from external APIs.
                Returns the newly created book details.
                """
        # Check the content type of the request to ensure it's JSON
        if request.headers['Content-Type'] != 'application/json':
            return {'error': 'Unsupported media type'}, 415

        # Initialize a request parser to validate and parse input data
        parser = reqparse.RequestParser()
        parser.add_argument('title', required=True, help="Title cannot be blank")
        parser.add_argument('ISBN', required=True, help="ISBN cannot be blank")
        parser.add_argument('genre', required=True, help="Genre cannot be blank")

        # Parse the input data
        try:
            args = parser.parse_args()
        except Exception as e:
            return {"error: Unprocessable Content"}, 422

        # Check if a book with the same ISBN already exists
        for book in books.values():  # Assuming 'books' is a dictionary where values are book details
            if book['ISBN'] == args['ISBN']:
                return {'error': 'A book with the same ISBN already exists'}, 422

        # Generate a unique ID for the book
        book_id = str(uuid.uuid4())

        # Fetch book data from an external API using the ISBN
        try:
            response = requests.get(f'{BASE_URL}?q=isbn:{args["ISBN"]}')
        except Exception as e:
            return {'error': 'Internal Server Error'}, 500
        book_data = response.json()['items'][0]['volumeInfo'] if response.ok and 'items' in response.json() else {}

        # Attempt to retrieve the language details for the book
        try:
            languages = get_languages(args["ISBN"])
        except Exception as e:
            return {'error': 'Internal Server Error'}, 500

        # Handle authors data, defaulting to "missing" if not available
        if len(book_data.get('authors', [])) < 1:
            authors = "missing"
        else:
            authors = book_data['authors'][0]
            if len(book_data['authors']) > 1:
                for author in book_data['authors'][1:]:
                    authors += " and " + author

        # Fill in the book details
        book_details = {
            'title': args['title'],
            'authors': authors,
            'ISBN': args['ISBN'],
            'publisher': book_data.get('publisher', 'missing'),
            'publishedDate': book_data.get('publishedDate', 'missing'),
            'genre': args['genre'],
            'languages': languages,
            'summary': getAIsummary(args['title'], authors),
            # 'language' and 'summary' would be fetched from OpenBooks API and LLM API, respectively
            'id': book_id,
        }

        # Store the new book in the in-memory data store
        books[book_id] = book_details
        ratings[book_id] = {
            'values': [],
            'average': 0,
            'title': args['title'],
            'id': book_id,
        }

        # Return the new book details with 201 Created status
        return book_id, 201


class Book(Resource):
    def get(self, book_id):
        """
                Retrieves a book by its ID from the books collection.
                Returns the book details if found, otherwise returns a 404 error.
                """
        # Check if the book is in our local 'database'
        if book_id in books:
            return books[book_id], 200
        else:
            return {'error': 'Book not found'}, 404

    def delete(self, book_id):
        """
               Deletes a book by its ID from the books collection.
               Returns the book ID if successful, otherwise returns a 404 error if the book is not found.
               """
        if book_id in books:
            del books[book_id]
            del ratings[book_id]
            return book_id, 200
        else:
            return {'error': 'Book not found'}, 404

    def put(self, book_id):
        """
              Updates the details of a specific book by book_id, validating and storing the provided data.
              """
        # Check the content type of the request to ensure it's JSON
        if request.headers['Content-Type'] != 'application/json':
            return {'error': 'Unsupported media type'}, 415
        data = request.get_json()
        # Verify that the book exists in the books dictionary using book_id
        if book_id not in books:
            return {'error': 'Book not found'}, 404
        else:
            # Initialize a request parser to validate and parse input data
            parser = reqparse.RequestParser()
            parser.add_argument('title', required=True, help="Title cannot be blank")
            parser.add_argument('ISBN', required=True, help="ISBN cannot be blank")
            parser.add_argument('genre', required=True, help="Genre cannot be blank")
            parser.add_argument('authors', required=True, help="Authors cannot be blank")
            parser.add_argument('publishedDate', required=True, help="publishedDate cannot be blank")
            parser.add_argument('languages', required=True, help="Languages cannot be blank")
            parser.add_argument('publisher', required=True, help="Publisher cannot be blank")
            parser.add_argument('id', required=True, help="ID cannot be blank")
            parser.add_argument('summary', required=True, help="Summary cannot be blank")

            try:
                # Parse the request arguments based on the defined rules
                args = parser.parse_args()
            except Exception as e:
                return {"error": "Unprocessable Content"}, 422

            # Construct a dictionary of the book details from parsed arguments
            book_details = {
                'title': args['title'],
                'authors': args['authors'],
                'ISBN': args['ISBN'],
                'publisher': args['publisher'],
                'publishedDate': args['publishedDate'],
                'genre': args['genre'],
                'languages': args['languages'],
                'summary': args['summary'],
                # 'language' and 'summary' would be fetched from OpenBooks API and LLM API, respectively
                'id': args['id']
            }

            books[book_id] = book_details

            return args['id'], 200


class Ratings(Resource):
    def get(self):
        """
            A Resource class to fetch ratings based on filter criteria provided through query parameters.
            """
        args = request.args  # Retrieve query parameters from the request
        # Start with all ratings
        filtered_ratings = ratings.values()

        # Iterate over each query parameter to apply filters
        for key, value in args.items():
            filtered_ratings = [rate for rate in filtered_ratings if str(rate.get(key)) == value]

        return {'ratings': list(filtered_ratings)}, 200


class Rating(Resource):
    def get(self, rate_id):
        """
            A Resource class to fetch ratings for a specific book using its rate_id.
            """
        # Check if the specified rate_id exists in the ratings dictionary
        if rate_id in ratings:
            return ratings[rate_id], 200
        else:  # No book exists with the given rate id, return an error message.
            return {'error': 'Book not found'}, 404


class RateValues(Resource):
    def post(self, rate_id):
        """
           A Resource class to handle the POST requests for adding new ratings to books.
           """
        # Check if the specified rate_id exists in the ratings dictionary
        if rate_id not in ratings:
            return {'error': 'Book not found'}, 404

        data = request.get_json()
        if request.headers['Content-Type'] != 'application/json':
            return {'error': 'Unsupported media type'}, 415  # Return error if content type is not JSON

        # Validate that the data includes a 'value' key and that the value is between 1 and 5
        if not data or 'value' not in data or not (1 <= data['value'] <= 5):
            return {"error": "Unprocessable Content"}, 422  # Return error if the value is not valid

        # Append the new value to the list of values for this book's ratings
        ratings[rate_id]['values'].append(data['value'])
        # Calculate the new average rating after adding the new value
        new_average = sum(ratings[rate_id]['values']) / len(ratings[rate_id]['values'])
        ratings[rate_id]['average'] = new_average

        return new_average, 201


class Top(Resource):
    """
        A Resource class to fetch the top-rated books from a collection based on at least 3 ratings.
        """

    def get(self):
        # Filter books that have at least 3 ratings.

        valid = {book_id: rate for book_id, rate in ratings.items() if len(rate['values']) >= 3}

        # Return an empty list if no books have sufficient ratings
        if len(valid) == 0:
            return [], 200, {'Content-Type': 'application/json'}

        answer_list = []

        # Sort valid books by average rating in descending order
        top_books_sorted = sorted(valid.items(), key=lambda item: item[1]['average'], reverse=True)

        max_books = min(3, len(top_books_sorted))  # Determine the number of top books to include

        # Add top 3 or fewer books to the answer list
        for i in range(max_books):
            book_id, rate = top_books_sorted[i]
            answer_list.append({
                'id': book_id,
                'title': books[book_id]['title'],
                'average': rate['average']
            })

        # Include additional books that have the same average rating as the last included book
        last_avg = answer_list[-1]['average'] if answer_list else None
        i += 1  # Move the index to the next book after the initial top set

        # Check for additional books with the same average rating
        while i < len(top_books_sorted) and top_books_sorted[i][1]['average'] == last_avg:
            book_id, rate = top_books_sorted[i]
            answer_list.append({
                'id': book_id,
                'title': books[book_id]['title'],
                'average': rate['average']
            })
            i += 1

        return answer_list, 200, {'Content-Type': 'application/json'}


api.add_resource(Books, '/books')
api.add_resource(Book, '/books/<string:book_id>')
api.add_resource(Ratings, '/ratings')
api.add_resource(Rating, '/ratings/<string:rate_id>')
api.add_resource(RateValues, '/ratings/<string:rate_id>/values')
api.add_resource(Top, '/top')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)