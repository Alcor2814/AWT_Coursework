const apiKey='2b739459da8dc4ec62f68656b642554dea026eca';
const url='https://www.comicvine.com/api/'
const format='&format=json'

console.log("script.js accessed");

function fetchData(){
	let query='&resources=character&query=Superman'
	let request = `https://comicvine.gamespot.com/api/search/?api_key=${apiKey}&format=json&resources=character&query=${query}`;
	
	try{
		fetch(request, {
			mode: 'cors'
			})
		  .then(response => response.json())
		  .then(data => console.log(data));
	}
	catch(error){
		console.error(error.message);
	}
}
	