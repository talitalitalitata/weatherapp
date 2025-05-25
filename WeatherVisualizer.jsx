import React, { useState, useEffect, useCallback } from 'react';

export default function WeatherVisualizer() {
  const [param, setParam] = useState('pm25');
  const [timeIndex, setTimeIndex] = useState(0);
  const [imageUrl, setImageUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [includeWind, setIncludeWind] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(false);
  const [timeOptions, setTimeOptions] = useState([]);
  const [date, setDate] = useState('04/03/2025');
  const [shareUrl, setShareUrl] = useState('');
  const [showShareModal, setShowShareModal] = useState(false);

  const maxTimeIndex = 23;

  useEffect(() => {
    const fetchTimeInfo = async () => {
      try {
        const response = await fetch('http://localhost:8000/time-info');
        const data = await response.json();
        setTimeOptions(data.times || []);
        setDate(data.date || '04/03/2025');
      } catch (err) {
        console.error("Failed to fetch time information:", err);
        const defaultTimes = Array.from({ length: 24 }, (_, i) => `${i.toString().padStart(2, '0')}:00`);
        setTimeOptions(defaultTimes);
      }
    };
    fetchTimeInfo();
  }, []);

  useEffect(() => {
    let animationInterval;
    if (isAnimating && isAnimationPlaying) {
      animationInterval = setInterval(() => {
        setTimeIndex(prev => (prev + 1) % (maxTimeIndex + 1));
      }, 500);
    }
    return () => clearInterval(animationInterval);
  }, [isAnimating, isAnimationPlaying]);

  const fetchStaticImage = useCallback(async () => {
    try {
      setIsLoading(true);
      setError('');
      const url = `http://localhost:8000/static-image?parameter=${param}&time_index=${timeIndex}&include_wind=${includeWind}&t=${Date.now()}`;
      setImageUrl(url);
    } catch (err) {
      setError('Gagal mengambil gambar. Pastikan server berjalan.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, [param, timeIndex, includeWind]);

  useEffect(() => {
    if (isAnimating && isAnimationPlaying) {
      fetchStaticImage();
    }
  }, [timeIndex, isAnimating, isAnimationPlaying, fetchStaticImage]);

  const fetchParameterAnimation = async () => {
    try {
      setIsLoading(true);
      setError('');
      setIsAnimating(false);
      const url = `http://localhost:8000/parameter-animation?parameter=${param}&include_wind=${includeWind}&t=${Date.now()}`;
      setImageUrl(url);
    } catch (err) {
      setError('Gagal mengambil animasi. Pastikan server berjalan.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleAnimation = () => {
    if (!isAnimating) {
      setIsAnimating(true);
      setIsAnimationPlaying(true);
    } else {
      setIsAnimationPlaying(prev => !prev);
    }
  };

  const stopAnimation = () => {
    setIsAnimating(false);
    setIsAnimationPlaying(false);
  };

  const handleTimeStep = (step) => {
    setTimeIndex(prev => {
      let newIndex = prev + step;
      if (newIndex < 0) newIndex = maxTimeIndex;
      if (newIndex > maxTimeIndex) newIndex = 0;
      return newIndex;
    });
    if (!isAnimating || !isAnimationPlaying) {
      setTimeout(fetchStaticImage, 10);
    }
  };

  const createShareableMap = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `http://localhost:8000/create-shareable-map?parameter=${param}&time_index=${timeIndex}&include_wind=${includeWind}`
      );
      const data = await response.json();
      if (data.success && data.share_url) {
        const fullUrl = `${window.location.origin}${data.share_url}`;
        setShareUrl(fullUrl);
        setShowShareModal(true);
      }
    } catch (err) {
      setError('Gagal membuat URL berbagi.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const parameters = [
    { value: 'rain', label: 'Curah Hujan' },
    { value: 'pm25', label: 'PM2.5' },
    { value: 'no2', label: 'NO₂' },
    { value: 'o3', label: 'O₃' },
    { value: 'u10', label: 'U10 (Angin Barat-Timur)' },
    { value: 'v10', label: 'V10 (Angin Utara-Selatan)' },
    { value: 'wind_vector', label: 'Vektor Angin' },
  ];

  return (
    <div className="p-6 max-w-4xl mx-auto bg-white rounded-lg shadow-lg">
      <h1 className="text-4xl font-bold mb-6 text-center text-blue-600">🌦️ Visualisasi Cuaca Indonesia</h1>
      <div className="mb-4 p-4 bg-blue-50 rounded-lg">
        <p className="text-gray-700">
          Aplikasi ini menampilkan visualisasi prakiraan cuaca untuk Indonesia menggunakan model WRF tanggal {date}.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="text-lg font-medium mb-2">Pilih Parameter:</label>
          <select
            value={param}
            onChange={(e) => {
              setParam(e.target.value);
              stopAnimation();
              setIncludeWind(false); // reset overlay jika perlu
            }}
            className="border border-blue-300 p-3 rounded-lg w-full"
          >
            {parameters.map(option => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-lg font-medium mb-2">Waktu:</label>
          <div className="flex">
            <button onClick={() => handleTimeStep(-1)} disabled={isAnimating && isAnimationPlaying} className="px-4 py-2 bg-blue-500 text-white rounded-l">◀</button>
            <select
              value={timeIndex}
              onChange={(e) => {
                setTimeIndex(+e.target.value);
                if (!isAnimating || !isAnimationPlaying) setTimeout(fetchStaticImage, 10);
              }}
              disabled={isAnimating && isAnimationPlaying}
              className="border-t border-b border-blue-300 p-2 text-center flex-grow"
            >
              {timeOptions.map((label, idx) => (
                <option key={idx} value={idx}>{label}</option>
              ))}
            </select>
            <button onClick={() => handleTimeStep(1)} disabled={isAnimating && isAnimationPlaying} className="px-4 py-2 bg-blue-500 text-white rounded-r">▶</button>
          </div>
        </div>
      </div>

      <div className="mb-4">
        <input
          type="checkbox"
          id="include-wind"
          checked={includeWind}
          onChange={(e) => setIncludeWind(e.target.checked)}
          disabled={param === 'wind_vector'}
          className="mr-2"
        />
        <label htmlFor="include-wind">Tampilkan Overlay Vektor Angin</label>
      </div>

      <div className="flex gap-4 justify-center mb-4 flex-wrap">
        <button onClick={fetchStaticImage} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg">Gambar Statis</button>
        <button onClick={fetchParameterAnimation} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg">Gambar Animasi</button>
        <button onClick={toggleAnimation} className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-lg">
          {isAnimationPlaying ? '⏸️ Pause' : '▶ Play'}
        </button>
        <button onClick={stopAnimation} className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg">⏹ Stop</button>
        <button onClick={createShareableMap} className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg">🔗 Bagikan</button>
      </div>

      {error && <div className="text-red-600 mb-4 text-center">{error}</div>}

      {imageUrl && (
        <div className="mb-4 text-center">
          <img src={imageUrl} alt="Visualisasi Cuaca" className="mx-auto max-w-full rounded-lg" />
        </div>
      )}

      {showShareModal && shareUrl && (
        <div className="bg-white border border-blue-300 p-4 rounded-lg shadow-lg text-center">
          <p className="mb-2">Bagikan peta ini:</p>
          <input
            type="text"
            value={shareUrl}
            readOnly
            className="w-full border border-gray-300 rounded p-2"
            onClick={(e) => e.target.select()}
          />
        </div>
      )}
    </div>
  );
}
