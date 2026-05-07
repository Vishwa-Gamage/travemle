from django.core.management.base import BaseCommand
from planner.models import Destination


DESTINATIONS = [
    {
        "name": "Sigiriya Rock Fortress",
        "country": "Sri Lanka",
        "category": "History",
        "description": "A UNESCO World Heritage Site, this ancient rock fortress rises 200m above the surrounding jungle. Home to stunning frescoes, water gardens, and breathtaking panoramic views.",
        "image_url": "https://images.unsplash.com/photo-1599561046251-bfb9465b4c44?w=800",
        "lat": 7.9570, "lon": 80.7603, "is_featured": True,
    },
    {
        "name": "Temple of the Tooth Relic, Kandy",
        "country": "Sri Lanka",
        "category": "Temple",
        "description": "Sri Lanka's most sacred Buddhist temple, housing the relic of the tooth of the Buddha. Set beside the serene Kandy Lake in the misty hills.",
        "image_url": "https://images.unsplash.com/photo-1588258524675-c61d5e360e25?w=800",
        "lat": 7.2936, "lon": 80.6412, "is_featured": True,
    },
    {
        "name": "Mirissa Beach",
        "country": "Sri Lanka",
        "category": "Beach",
        "description": "A stunning crescent-shaped beach on Sri Lanka's south coast, famous for whale watching, surfing, and spectacular sunsets. One of the best beaches in Asia.",
        "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
        "lat": 5.9483, "lon": 80.4716, "is_featured": True,
    },
    {
        "name": "Ella Nine Arch Bridge",
        "country": "Sri Lanka",
        "category": "Nature",
        "description": "One of Sri Lanka's most iconic landmarks, this colonial-era railway bridge is surrounded by lush tea plantations and misty mountains. Perfect for photography.",
        "image_url": "https://images.unsplash.com/photo-1586771107445-d3ca888129ff?w=800",
        "lat": 6.8753, "lon": 81.0582, "is_featured": True,
    },
    {
        "name": "Yala National Park",
        "country": "Sri Lanka",
        "category": "Wildlife",
        "description": "Sri Lanka's most visited national park, home to the world's highest density of leopards. Also hosts elephants, sloth bears, crocodiles, and hundreds of bird species.",
        "image_url": "https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?w=800",
        "lat": 6.3728, "lon": 81.5196, "is_featured": True,
    },
    {
        "name": "Nuwara Eliya",
        "country": "Sri Lanka",
        "category": "Nature",
        "description": "Known as 'Little England', this hill station at 1,868m offers cool climate, colonial bungalows, and endless emerald tea plantations. Perfect for a scenic train ride.",
        "image_url": "https://images.unsplash.com/photo-1561901836-09a7acf9ae37?w=800",
        "lat": 6.9497, "lon": 80.7891, "is_featured": False,
    },
    {
        "name": "Galle Fort",
        "country": "Sri Lanka",
        "category": "History",
        "description": "A UNESCO-listed 17th-century Dutch fort on the southwest coast. Explore cobblestone streets, boutique shops, cafes, and colonial architecture within ancient ramparts.",
        "image_url": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800",
        "lat": 6.0260, "lon": 80.2170, "is_featured": False,
    },
    {
        "name": "Arugam Bay",
        "country": "Sri Lanka",
        "category": "Adventure",
        "description": "A world-famous surf destination on the east coast. Arugam Bay offers consistent waves, a laid-back beach town vibe, and nearby wildlife sanctuaries.",
        "image_url": "https://images.unsplash.com/photo-1520520731457-9283dd14aa66?w=800",
        "lat": 6.8400, "lon": 81.8357, "is_featured": False,
    },
    {
        "name": "Dambulla Cave Temple",
        "country": "Sri Lanka",
        "category": "Temple",
        "description": "The largest cave temple complex in Sri Lanka, featuring 153 Buddha statues and paintings covering 2,100 sq.m. Another UNESCO World Heritage Site.",
        "image_url": "https://images.unsplash.com/photo-1605649487212-47bdab064df7?w=800",
        "lat": 7.8568, "lon": 80.6492, "is_featured": False,
    },
    {
        "name": "Horton Plains National Park",
        "country": "Sri Lanka",
        "category": "Nature",
        "description": "A highland plateau with misty grasslands, cloud forests, and World's End - a dramatic 870m cliff drop. Home to sambar deer and the elusive fishing cat.",
        "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800",
        "lat": 6.8028, "lon": 80.8042, "is_featured": False,
    },
    {
        "name": "Colombo Street Food Scene",
        "country": "Sri Lanka",
        "category": "Food",
        "description": "Sri Lanka's capital offers a vibrant street food culture. Try kottu roti, hoppers, string hoppers, and fresh seafood at Galle Face Green and Manning Market.",
        "image_url": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800",
        "lat": 6.9271, "lon": 79.8612, "is_featured": False,
    },
    {
        "name": "Trincomalee",
        "country": "Sri Lanka",
        "category": "Beach",
        "description": "Home to one of the world's finest natural harbors. Enjoy crystal-clear waters, whale watching, diving, and the ancient Koneswaram Temple perched on a cliff.",
        "image_url": "https://images.unsplash.com/photo-1559128010-7c1ad6e1b6a5?w=800",
        "lat": 8.5667, "lon": 81.2333, "is_featured": False,
    },
]


class Command(BaseCommand):
    help = "Seed the database with initial Sri Lanka destinations"

    def handle(self, *args, **options):
        created, skipped = 0, 0
        for dest_data in DESTINATIONS:
            obj, was_created = Destination.objects.get_or_create(
                name=dest_data["name"],
                country=dest_data["country"],
                defaults=dest_data,
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  [OK] Created: {obj.name}"))
            else:
                skipped += 1
                self.stdout.write(f"  [--] Skipped: {obj.name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone! {created} destinations created, {skipped} already existed."
            )
        )
