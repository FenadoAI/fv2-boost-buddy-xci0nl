import { useEffect } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import axios from "axios";
import Signup from "./pages/Signup";
import Login from "./pages/Login";
import Chat from "./pages/Chat";

// BACKEND URL
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';
const API = `${API_BASE}/api`;

// THIS IS WHERE OUR WEBSITE IS HOSTED, [ generate share links relative to this url ]
const MY_HOMEPAGE_URL = API_BASE?.match(/-([a-z0-9]+)\./)?.[1]
  ? `https://${API_BASE?.match(/-([a-z0-9]+)\./)?.[1]}.previewer.live`
  : window.location.origin;

console.log(`MY_HOMEPAGE_URL: ${MY_HOMEPAGE_URL}`);

const Home = () => {
  const helloWorldApi = async () => {
    try {
      const response = await axios.get(`${API}/`);
      console.log(response.data.message);
    } catch (e) {
      console.error(e, `errored out requesting / api`);
    }
  };

  useEffect(() => {
    helloWorldApi();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
      <div className="text-center px-4">
        <div className="mb-8">
          <h1 className="text-5xl font-bold text-gray-800 mb-4">
            Welcome to Motivational Chat
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Your 24/7 AI companion for positivity and encouragement
          </p>
        </div>

        <div className="space-x-4 mb-12">
          <Link
            to="/signup"
            className="inline-block px-8 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors shadow-lg"
          >
            Get Started
          </Link>
          <Link
            to="/login"
            className="inline-block px-8 py-3 bg-white text-blue-600 border-2 border-blue-600 rounded-lg font-medium hover:bg-blue-50 transition-colors"
          >
            Log In
          </Link>
        </div>

        <div className="max-w-2xl mx-auto bg-white p-8 rounded-xl shadow-lg">
          <h2 className="text-2xl font-semibold text-gray-800 mb-4">What We Offer</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
            <div className="p-4">
              <div className="text-3xl mb-2">💬</div>
              <h3 className="font-semibold mb-2">Supportive Chat</h3>
              <p className="text-sm text-gray-600">
                Have meaningful conversations with an AI that truly cares
              </p>
            </div>
            <div className="p-4">
              <div className="text-3xl mb-2">✨</div>
              <h3 className="font-semibold mb-2">Daily Quotes</h3>
              <p className="text-sm text-gray-600">
                Receive inspiring quotes to brighten your day
              </p>
            </div>
            <div className="p-4">
              <div className="text-3xl mb-2">🌟</div>
              <h3 className="font-semibold mb-2">24/7 Availability</h3>
              <p className="text-sm text-gray-600">
                Get encouragement whenever you need it
              </p>
            </div>
          </div>
        </div>

        <footer className="mt-12 text-gray-600">
          <p className="text-sm">
            Powered by Fenado AI •{" "}
            <Link to="/chat" className="text-blue-600 hover:underline">
              Chat Now
            </Link>
          </p>
        </footer>
      </div>
    </div>
  );
};

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/login" element={<Login />} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
