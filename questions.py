# Political Compass Test propositions
# Source: politicalcompass.org
# Each question is tagged with its axis:
#   "econ" = economic left/right axis
#   "social" = authoritarian/libertarian axis
# sign: +1 = agree moves toward right/authoritarian, -1 = agree moves toward left/libertarian
# Axis scoring convention (matching politicalcompass.org):
#   Economic: negative = left, positive = right
#   Social: negative = libertarian, positive = authoritarian

QUESTIONS = [
    # Page 1 — Global/National
    {
        "id": 1,
        "text": "If economic globalisation is inevitable, it should primarily serve humanity rather than the interests of trans-national corporations.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 2,
        "text": "I'd always support my country, whether it was right or wrong.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 3,
        "text": "No one chooses their country of birth, so it's foolish to be proud of it.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 4,
        "text": "Our race has many superior qualities, compared with other races.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 5,
        "text": "The enemy of my enemy is my friend.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 6,
        "text": "Military action that defies international law is sometimes justified.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 7,
        "text": "There is now a worrying fusion of information and entertainment.",
        "axis": "social",
        "sign": -1,
    },
    # Page 2 — Economy
    {
        "id": 8,
        "text": "People are ultimately divided more by class than by nationality.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 9,
        "text": "Controlling inflation is more important than controlling unemployment.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 10,
        "text": "Because corporations cannot be trusted to voluntarily protect the environment, they require regulation.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 11,
        "text": "\"from each according to his ability, to each according to his need\" is a fundamentally good idea.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 12,
        "text": "The freer the market, the freer the people.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 13,
        "text": "It's a sad reflection on our society that something as basic as drinking water is now a bottled, branded consumer product.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 14,
        "text": "Land shouldn't be a commodity to be bought and sold.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 15,
        "text": "It is regrettable that many personal fortunes are made by people who simply manipulate money and contribute nothing to their society.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 16,
        "text": "Protectionism is sometimes necessary in trade.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 17,
        "text": "The only social responsibility of a company should be to deliver a profit to its shareholders.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 18,
        "text": "The rich are too highly taxed.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 19,
        "text": "Those with the ability to pay should have access to higher standards of medical care.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 20,
        "text": "Governments should penalise businesses that mislead the public.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 21,
        "text": "A genuine free market requires restrictions on the ability of predator multinationals to create monopolies.",
        "axis": "econ",
        "sign": -1,
    },
    # Page 3 — Personal/Social values
    {
        "id": 22,
        "text": "Abortion, when the woman's life is not threatened, should always be illegal.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 23,
        "text": "All authority should be questioned.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 24,
        "text": "An eye for an eye and a tooth for a tooth.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 25,
        "text": "Taxpayers should not be expected to prop up any theatres or museums that cannot survive on a commercial basis.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 26,
        "text": "Schools should not make classroom attendance compulsory.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 27,
        "text": "All people have their rights, but it is better for all of us that different sorts of people should keep to their own kind.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 28,
        "text": "Good parents sometimes have to spank their children.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 29,
        "text": "It's natural for children to keep some secrets from their parents.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 30,
        "text": "Possessing marijuana for personal use should not be a criminal offence.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 31,
        "text": "The prime function of schooling should be to equip the future generation to find jobs.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 32,
        "text": "People with serious inheritable disabilities should not be allowed to reproduce.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 33,
        "text": "The most important thing for children to learn is to accept discipline.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 34,
        "text": "There are no savage and civilised peoples; there are only different cultures.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 35,
        "text": "Those who are able to work, and refuse the opportunity, should not expect society's support.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 36,
        "text": "When you are troubled, it's better not to think about it, but to keep busy with more cheerful things.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 37,
        "text": "First-generation immigrants can never be fully integrated within their new country.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 38,
        "text": "What's good for the most successful corporations is always, ultimately, good for all of us.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 39,
        "text": "No broadcasting institution, however independent its content, should receive public funding.",
        "axis": "econ",
        "sign": +1,
    },
    # Page 4 — Wider society
    {
        "id": 40,
        "text": "Our civil liberties are being excessively curbed in the name of counter-terrorism.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 41,
        "text": "A significant advantage of a one-party state is that it avoids all the arguments that delay progress in a democratic political system.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 42,
        "text": "Although the electronic age makes official surveillance easier, only wrongdoers need to be worried.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 43,
        "text": "The death penalty should be an option for the most serious crimes.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 44,
        "text": "In a civilised society, one must always have people above to be obeyed and people below to be commanded.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 45,
        "text": "Abstract art that doesn't represent anything shouldn't be considered art at all.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 46,
        "text": "In criminal justice, punishment should be more important than rehabilitation.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 47,
        "text": "It is a waste of time to try to rehabilitate some criminals.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 48,
        "text": "The businessperson and the manufacturer are more important than the writer and the artist.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 49,
        "text": "Mothers may have careers, but their first duty is to be homemakers.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 50,
        "text": "Almost all politicians promise economic growth, but we should heed the warnings of climate science that growth is detrimental to our efforts to curb global warming.",
        "axis": "econ",
        "sign": -1,
    },
    {
        "id": 51,
        "text": "Making peace with the establishment is an important aspect of maturity.",
        "axis": "social",
        "sign": +1,
    },
    # Page 5 — Religion
    {
        "id": 52,
        "text": "Astrology accurately explains many things.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 53,
        "text": "You cannot be moral without being religious.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 54,
        "text": "Charity is better than social security as a means of helping the genuinely disadvantaged.",
        "axis": "econ",
        "sign": +1,
    },
    {
        "id": 55,
        "text": "Some people are naturally unlucky.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 56,
        "text": "It is important that my child's school instils religious values.",
        "axis": "social",
        "sign": +1,
    },
    # Page 6 — Sex and gender
    {
        "id": 57,
        "text": "Sex outside marriage is usually immoral.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 58,
        "text": "A same sex couple in a stable, loving relationship should not be excluded from the possibility of child adoption.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 59,
        "text": "Pornography, depicting consenting adults, should be legal for the adult population.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 60,
        "text": "What goes on in a private bedroom between consenting adults is no business of the state.",
        "axis": "social",
        "sign": -1,
    },
    {
        "id": 61,
        "text": "No one can feel naturally homosexual.",
        "axis": "social",
        "sign": +1,
    },
    {
        "id": 62,
        "text": "These days openness about sex has gone too far.",
        "axis": "social",
        "sign": +1,
    },
]

RESPONSE_OPTIONS = ["Strongly Disagree", "Disagree", "Agree", "Strongly Agree"]

# Maps response string -> raw score before sign flip
RESPONSE_TO_RAW = {
    "Strongly Disagree": -2,
    "Disagree": -1,
    "Agree": +1,
    "Strongly Agree": +2,
}
