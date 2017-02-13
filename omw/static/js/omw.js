
$( document ).ready(function() {
    $.getJSON($SCRIPT_ROOT + '/_load_lang_selector', {
    }, function(data) {
	var langsel = document.getElementById("LangSelector");
	langsel.innerHTML = data.result;
    });
});






///////////////////////////////////////////////////////////////////
// HERE IS THE OMWEDIT, EVERYTHING IS STILL HIGHLY EXPERIMENTAL! 
///////////////////////////////////////////////////////////////////

$(function() {
   $("#add_new_definition").click(function (event) {


       var htmltxt = "<br><table cellpadding='0' cellspacing='0' border='0'> \
                      <tr><td>Definition:</td><td><input id='def'></input></td></tr>\
                      <tr><td>Lang</td><td><input id='lang'></input></td></tr>\
                      </table>";

       swal({
	   title: 'Add New Definition',
	   showCancelButton: true,
	   confirmButtonText: 'Add Definiiton!',
	   cancelButtonText: 'No, cancel!',
	   buttonsStyling: false,
	   html: htmltxt,

	   preConfirm: function() {
	       return new Promise(function(resolve) {

		   var result = resolve([
		       $('#def').val(),
		       $('#lang').val()
		   ]);

	       });
	   }
       }).then(function(result) {


	   $.getJSON($SCRIPT_ROOT + '/_add_new_definition', {
	       // user: $('input[name="current_user"]').val(),
	       def: result[0],
	       lang: result[1],
	   }, function(data) {

	       if (data.result) {
		   swal("The new definition was added!", 
			"New def: " + result , "success");
	       } else {
		   swal("Something went wrong.", 
			"You need to provide at least a definition"+
			"and code and a language." , "error");
	       }

	   });
       })
       return false;
   });
});



$(function() {
   $("#edit_definition").click(function (event) {


       var htmltxt = "<br><table cellpadding='0' cellspacing='0' border='0'> \
                      <tr><td>Definition:</td><td><input id='def'></input></td></tr>\
                      </table>";

       swal({
	   title: 'Edit Definition',
	   showCancelButton: true,
	   confirmButtonText: 'Commit Changes!',
	   cancelButtonText: 'No, cancel!',
	   buttonsStyling: false,
	   html: htmltxt,

	   preConfirm: function() {
	       return new Promise(function(resolve) {

		   var result = resolve([
		       $('#def').val()
		   ]);

	       });
	   }
       }).then(function(result) {


	   $.getJSON($SCRIPT_ROOT + '/_edit_definition', {
	       // user: $('input[name="current_user"]').val(),
	       def: result[0],
	   }, function(data) {

	       if (data.result) {
		   swal("The new definition was changed!", 
			"New def: " + result,
			"success");
	       } else {
		   swal("Something went wrong.", 
			"Please report this..." ,
			"error");
	       }

	   });
       })
       return false;
   });
});




/// EDITING EXAMPLES

/// TRY TO GET A DIFFERENT WAY OF EDITING EXAMPLES
$(function() {
    $("#edit_examples").click(function (event) {
	var target = '#examples-detailed';
    $.getJSON($SCRIPT_ROOT + '/_edit_examples', {
	    proj: $('input[name="projID"]').val(),
	    ss: $('input[name="ssID"]').val()
	}, function(data) {
	    $(target).html(data.result);
	});
	return false;
    });
});


$(function() {
   $("#add_new_example, #add_new_example_quick").click(function (event) {

       var langs = $('#main_lang_selector').html();

       var htmltxt = "<br><table cellpadding='0' cellspacing='0' border='0'> \
                      <tr><td>Example:</td><td><input id='txt'></input></td></tr>\
                      <tr><td>Lang</td><td><select id='new_ssex_lang' style='font-size:\
                      85%; width: 9em' required>" + langs + "</select></td></tr></table>";

       swal({
	   title: 'Add New Example',
	   showCancelButton: true,
	   confirmButtonText: 'Add Example!',
	   cancelButtonText: 'No, cancel!',
	   buttonsStyling: false,
	   html: htmltxt,

	   preConfirm: function() {
	       return new Promise(function(resolve) {

		   var result = resolve([
		       $('#txt').val(),
		       $('#new_ssex_lang').val(),
		       $('#ssID').val(),
		       $('#projID').val()
		   ]);
	       });
	   }
       }).then(function(result) {

	   $.getJSON($SCRIPT_ROOT + '/_add_new_example', {
	       // user: $('input[name="current_user"]').val(),
	       txt: result[0],
	       lang: result[1],
	       ss: result[2],
	       proj: result[3],
	   }, function(data) {

	       if (data.result) {
		   swal("The new example was added!", 
			"New example: " + result , "success");
	       } else {
		   swal("Something went wrong.", 
			"You need to provide at least an example "+
			"and a language." , "error");
	       }

	   });
       })
       return false;
   });
});
