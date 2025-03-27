
import os
import zipfile
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

def fetch_places(api_key, location, radius, keyword, min_rating):
    endpoint = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": api_key,
        "location": location,
        "radius": radius,
        "keyword": keyword
    }
    try:
        res = requests.get(endpoint, params=params)
        res.raise_for_status()
        data = res.json()
        results = [
            {
                "name": p["name"],
                "lat": p["geometry"]["location"]["lat"],
                "lng": p["geometry"]["location"]["lng"],
                "rating": p["rating"]
            }
            for p in data.get("results", [])
            if p.get("rating", 0) >= min_rating
        ]
        return results
    except Exception as e:
        raise RuntimeError(f"Failed to fetch places: {e}")

def create_kml(places):
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<kml xmlns="http://www.opengis.net/kml/2.2">',
        '<Document>'
    ]
    for p in places:
        lines.append(f'''
        <Placemark>
            <name>{p["name"]}</name>
            <description>Rating: {p["rating"]}</description>
            <Point><coordinates>{p["lng"]},{p["lat"]},0</coordinates></Point>
        </Placemark>
        ''')
    lines.append('</Document></kml>')
    return '\n'.join(lines)

def write_kmz(kml_str, out_file):
    temp_kml = os.path.join(os.getcwd(), "temp.kml")
    with open(temp_kml, 'w', encoding='utf-8') as f:
        f.write(kml_str)
    with zipfile.ZipFile(out_file, 'w', zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(temp_kml, arcname="doc.kml")
    os.remove(temp_kml)

@app.route("/generate-map", methods=["POST"])
def generate():
    try:
        body = request.json
        api_key = body["api_key"]
        location = body["location"]
        keyword = body["keyword"]
        radius = body.get("radius", 3000)
        min_rating = body.get("min_rating", 4.0)

        places = fetch_places(api_key, location, radius, keyword, min_rating)
        if not places:
            return jsonify({"error": "No matching places found."}), 404

        kml_data = create_kml(places)
        kmz_path = os.path.join(os.getcwd(), "output.kmz")
        write_kmz(kml_data, kmz_path)

        return jsonify({
            "message": "KMZ file created. Upload it to Google My Maps (Import > Upload file).",
            "file": kmz_path
        })

    except KeyError as e:
        return jsonify({"error": f"Missing field: {e}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
