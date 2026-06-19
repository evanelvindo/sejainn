import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# Setup logging untuk memantau kegagalan API Geocoding
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(message)s')

def get_address_from_coords(lat: float, lon: float) -> str:
    """
    Mengubah koordinat Latitude dan Longitude menjadi alamat fisik (Reverse Geocoding).
    Menggunakan OpenStreetMap Nominatim API.
    """
    try:
        # User-agent harus unik sesuai kebijakan Nominatim
        geolocator = Nominatim(user_agent="sejaiin_hub_app_v1")
        
        # Menambahkan timeout karena API gratis seringkali lambat merespons
        location = geolocator.reverse(
            f"{lat}, {lon}", 
            language='id', 
            timeout=10
        )
        
        if location:
            # Mengambil alamat lengkap
            return location.address
        else:
            return "Alamat tidak terdeteksi di koordinat tersebut"

    except GeocoderTimedOut:
        logging.error(f"Geocoding Timeout untuk koordinat: {lat}, {lon}")
        return "Gagal memuat alamat (Waktu habis)"
    
    except GeocoderServiceError as e:
        logging.error(f"Geocoding Service Error: {e}")
        return "Layanan alamat sedang gangguan"
        
    except Exception as e:
        logging.error(f"Unexpected Geocoding Error: {e}")
        return "Alamat tidak dapat dimuat saat ini"

def format_wa_number(phone_number: str) -> str:
    """
    Utility tambahan untuk memastikan nomor WhatsApp selalu dalam format 
    internasional (62) tanpa karakter spesial.
    """
    clean_number = "".join(filter(str.isdigit, str(phone_number)))
    
    if clean_number.startswith('0'):
        clean_number = '62' + clean_number[1:]
    elif clean_number.startswith('8'):
        clean_number = '62' + clean_number
        
    return clean_number