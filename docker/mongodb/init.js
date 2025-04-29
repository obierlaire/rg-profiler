// MongoDB initialization script for RG Profiler

// Switch to the admin database to create user
db = db.getSiblingDB('admin');

// Create admin user if it doesn't exist 
if (db.getUser("benchmarkdbuser") == null) {
    db.createUser({
        user: "benchmarkdbuser",
        pwd: "benchmarkdbpass",
        roles: [
            { role: "userAdminAnyDatabase", db: "admin" },
            { role: "readWriteAnyDatabase", db: "admin" },
            { role: "dbAdminAnyDatabase", db: "admin" }
        ]
    });
}

// Switch to the hello_world database
db = db.getSiblingDB('hello_world');

// Create collections
db.createCollection('world');
db.createCollection('fortune');
db.createCollection('users');
db.createCollection('sessions');
db.createCollection('complex_data');

// Create indexes
db.world.createIndex({ id: 1 }, { unique: true });
db.fortune.createIndex({ id: 1 }, { unique: true });
db.users.createIndex({ username: 1 }, { unique: true });
db.sessions.createIndex({ user_id: 1 });
db.sessions.createIndex({ expires_at: 1 }, { expireAfterSeconds: 0 });
db.complex_data.createIndex({ name: 1 });
db.complex_data.createIndex({ "tags": 1 });

// Populate World collection if empty
if (db.world.countDocuments() === 0) {
    const worldDocs = [];
    for (let i = 1; i <= 10000; i++) {
        worldDocs.push({
            id: i,
            randomnumber: Math.floor(Math.random() * 10000) + 1
        });
    }
    db.world.insertMany(worldDocs);
    print(`Inserted ${worldDocs.length} documents into world collection`);
}

// Populate Fortune collection if empty
if (db.fortune.countDocuments() === 0) {
    db.fortune.insertMany([
        { id: 1, message: 'fortune: No such file or directory' },
        { id: 2, message: 'A computer scientist is someone who fixes things that aren\'t broken.' },
        { id: 3, message: 'After enough decimal places, nobody gives a damn.' },
        { id: 4, message: 'A bad random number generator: 1, 1, 1, 1, 1, 4.33e+67, 1, 1, 1' },
        { id: 5, message: 'A computer program does what you tell it to do, not what you want it to do.' },
        { id: 6, message: 'Emacs is a nice operating system, but I prefer UNIX. — Tom Christaensen' },
        { id: 7, message: 'Any program that runs right is obsolete.' },
        { id: 8, message: 'A list is only as strong as its weakest link. — Donald Knuth' },
        { id: 9, message: 'Feature: A bug with seniority.' },
        { id: 10, message: 'Computers make very fast, very accurate mistakes.' },
        { id: 11, message: '<script>alert("This should not be displayed in a browser alert box.");</script>' },
        { id: 12, message: 'フレームワークのベンチマーク' }
    ]);
    print("Inserted 12 documents into fortune collection");
}

// Populate users collection if empty
if (db.users.countDocuments() === 0) {
    db.users.insertMany([
        {
            username: 'testuser',
            password: 'password123',
            email: 'test@example.com',
            created_at: new Date()
        },
        {
            username: 'john',
            password: 'securepass',
            email: 'john@example.com',
            created_at: new Date()
        },
        {
            username: 'alice',
            password: 'pass123',
            email: 'alice@example.com',
            created_at: new Date()
        }
    ]);
    print("Inserted 3 documents into users collection");
}

// Populate complex_data collection if empty
if (db.complex_data.countDocuments() === 0) {
    db.complex_data.insertMany([
        {
            name: 'Item 1',
            data: {
                properties: { color: 'red', size: 'large' },
                metrics: { views: 123, likes: 42 },
                nested: { level1: { level2: { value: 42 } } }
            },
            tags: ['tag1', 'tag2', 'red'],
            created_at: new Date()
        },
        {
            name: 'Item 2',
            data: {
                properties: { color: 'blue', size: 'medium' },
                metrics: { views: 56, likes: 8 },
                nested: { level1: { level2: { value: 18 } } }
            },
            tags: ['tag3', 'tag2', 'blue'],
            created_at: new Date()
        },
        {
            name: 'Item 3',
            data: {
                properties: { color: 'green', size: 'small' },
                metrics: { views: 987, likes: 241 },
                nested: { level1: { level2: { value: 99 } } }
            },
            tags: ['tag1', 'tag4', 'green'],
            created_at: new Date()
        }
    ]);
    print("Inserted 3 documents into complex_data collection");
}

print('MongoDB initialization completed');
