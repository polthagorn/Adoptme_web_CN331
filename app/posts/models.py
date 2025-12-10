from django.db import models
from django.contrib.auth.models import User
from app.shelters.models import ShelterProfile


# ================================
# TAG MODEL
# ================================
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ================================
# TAG CHOICES (for Post.tag)
# ================================
TAG_CHOICES = [
    ('none', 'ไม่มีแท็ก'),
    ('missing', 'สัตว์หาย'),
    ('adoption_update', 'อัปเดตการรับเลี้ยง'),
    ('qa', 'Q&A'),
    ('other', 'อื่นๆ'),
    ('care', 'เคล็ดลับการดูแลสัตว์'),
    ('health', 'สุขภาพ/หมอ'),
    ('success', 'เรื่องราวความสำเร็จ'),
    ('event', 'กิจกรรมรับเลี้ยง'),
    ('found', 'พบสัตว์หลง'),
]


# ================================
# ANIMAL TYPE & RACE CHOICES
# ================================
ANIMAL_TYPE_CHOICES = [
    ("dog", "Dog"),
    ("cat", "Cat"),
    ("fox", "Fox"),
    ("rabbit", "Rabbit"),
    ("hamster", "Hamster"),
    ("small_pet", "Small Pet (Guinea Pig, Ferret, etc.)"),
    ("bird", "Bird"),
    ("reptile", "Reptile"),
    ("fish", "Fish / Aquatic"),
    ("invertebrate", "Invertebrate"),
    ("other", "Other"),
]

PET_RACE_CHOICES = [
    # Dogs
    ("golden_retriever", "Golden Retriever"),
    ("labrador_retriever", "Labrador Retriever"),
    ("german_shepherd", "German Shepherd"),
    ("siberian_husky", "Siberian Husky"),
    ("beagle", "Beagle"),
    ("border_collie", "Border Collie"),
    ("australian_shepherd", "Australian Shepherd"),
    ("rottweiler", "Rottweiler"),
    ("doberman", "Doberman"),
    ("great_dane", "Great Dane"),
    ("chihuahua", "Chihuahua"),
    ("pomeranian", "Pomeranian"),
    ("pug", "Pug"),
    ("shih_tzu", "Shih Tzu"),
    ("yorkshire_terrier", "Yorkshire Terrier"),
    ("corgi", "Corgi"),
    ("maltese", "Maltese"),

    # Cats
    ("domestic_shorthair", "Domestic Shorthair"),
    ("domestic_longhair", "Domestic Longhair"),
    ("siamese", "Siamese"),
    ("persian", "Persian"),
    ("maine_coon", "Maine Coon"),
    ("british_shorthair", "British Shorthair"),
    ("scottish_fold", "Scottish Fold"),
    ("bengal", "Bengal"),
    ("ragdoll", "Ragdoll"),
    ("sphynx", "Sphynx"),
    ("russian_blue", "Russian Blue"),

    # Foxes
    ("fennec_fox", "Fennec Fox"),
    ("red_fox", "Red Fox"),
    ("silver_fox", "Silver Fox"),
    ("cross_fox", "Cross Fox"),
    ("marble_fox", "Marble Fox"),
    ("platinum_fox", "Platinum Fox"),
    ("arctic_fox", "Arctic Fox"),
    ("pale_fox", "Pale Fox"),

    # Rabbits
    ("holland_lop", "Holland Lop"),
    ("netherland_dwarf", "Netherland Dwarf"),
    ("lionhead", "Lionhead"),
    ("mini_rex", "Mini Rex"),
    ("flemish_giant", "Flemish Giant"),

    # Small pets
    ("syrian_hamster", "Syrian Hamster"),
    ("winter_white_hamster", "Winter White Dwarf Hamster"),
    ("roborovski_hamster", "Roborovski Dwarf Hamster"),
    ("campbells_hamster", "Campbell's Dwarf Hamster"),
    ("chinese_hamster", "Chinese Hamster"),
    ("guinea_pig", "Guinea Pig"),
    ("ferret", "Ferret"),
    ("hedgehog", "Hedgehog"),
    ("chinchilla", "Chinchilla"),
    ("sugar_glider", "Sugar Glider"),

    # Reptiles / Amphibians
    ("leopard_gecko", "Leopard Gecko"),
    ("crested_gecko", "Crested Gecko"),
    ("tokay_gecko", "Tokay Gecko"),
    ("bearded_dragon", "Bearded Dragon"),
    ("green_iguana", "Green Iguana"),
    ("blue_tongue_skink", "Blue-Tongue Skink"),
    ("corn_snake", "Corn Snake"),
    ("ball_python", "Ball Python"),
    ("king_snake", "King Snake"),
    ("milk_snake", "Milk Snake"),
    ("axolotl", "Axolotl"),

    # Birds
    ("budgie", "Budgie / Parakeet"),
    ("cockatiel", "Cockatiel"),
    ("lovebird", "Lovebird"),
    ("canary", "Canary"),
    ("finch", "Finch"),
    ("african_grey", "African Grey Parrot"),
    ("macaw", "Macaw"),
    ("cockatoo", "Cockatoo"),
    ("sun_conure", "Sun Conure"),
    ("eclectus", "Eclectus Parrot"),

    # Aquatic
    ("goldfish", "Goldfish"),
    ("betta", "Betta"),
    ("guppy", "Guppy"),
    ("discus", "Discus"),
    ("arowana", "Arowana"),

    # Invertebrates
    ("tarantula", "Tarantula"),
    ("scorpion", "Scorpion"),
    ("giant_african_snail", "Giant African Land Snail"),
    ("hermit_crab", "Hermit Crab"),

    # Fallback
    ("other", "Other / Mixed"),
]


# ================================
# POST MODEL
# ================================
class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    shelter = models.ForeignKey(
        ShelterProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='posts'
    )

    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='post_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    tag = models.CharField(max_length=50, choices=TAG_CHOICES, default='none')

    # 🐾 NEW FIELDS
    animal_type = models.CharField(
        max_length=20,
        choices=ANIMAL_TYPE_CHOICES,
        default="dog",
        blank=True,
        null=True,
    )
    animal_race = models.CharField(
        max_length=50,
        choices=PET_RACE_CHOICES,
        default="other",
        blank=True,
        null=True,
    )

    location = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    bookmarks = models.ManyToManyField(User, related_name='bookmarked_posts', blank=True)

    def __str__(self):
        return self.title


# ================================
# COMMENT MODEL
# ================================
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'
