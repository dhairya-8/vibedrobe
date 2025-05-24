jQuery(document).ready(function($){
  $('.menu li a').click(function(){
    var target = $(this).attr('href');
    var height_header = $('.action-top-menu').height();
        $('html, body').animate({
            scrollTop: $(target).offset().top - height_header
        }, 1000);
        return false;
    });
  var height_header = $('.action-top-menu').outerHeight();
  if(height_header > 1){
    //$("#wrapper").css("padding-top", height_header); 
  }
  $(window).scroll(function() {
    if( $(this).scrollTop() > height_header ) {
      $('.action-top-menu').addClass('stick');
    } else {
      $('.action-top-menu').removeClass('stick');
    }
  });
  // add slick
  $(document).ready(function(){
    $('.slick-responsive').slick({
      dots: true,
      arrows: false,
      infinite:false ,
      speed: 300,
      slidesToShow: 5,
      slidesToScroll: 5,
      responsive: [
        {
          breakpoint: 1024,
          settings: {
            slidesToShow: 4,
            slidesToScroll: 4,
            infinite: true,
            dots: true
          }
        },
        {
          breakpoint: 600,
          settings: {
            slidesToShow: 3,
            slidesToScroll: 3
          }
        },
        {
          breakpoint: 480,
          settings: {
            slidesToShow: 2,
            slidesToScroll: 2
          }
        }
      ]
    });

    });


    $('.isotope-items').each(function(){  
        var $container = $(this);
        
        $container.imagesLoaded( function(){
            $container.isotope({
                itemSelector : '.isotope-item',
                transformsEnabled: true,         // Important for videos
                masonry: {
                    columnWidth: $container.data('columnwidth')
                }
            }); 
        });
    });

    /*---------------------------------------------- 
     *    Apply Filter        
     *----------------------------------------------*/
    $('.isotope-filter li a').on('click', function(){
       
        var parentul = $(this).parents('ul.isotope-filter').data('related-grid');
        $(this).parents('ul.isotope-filter').find('li a').removeClass('active');
        $(this).addClass('active');
        var selector = $(this).attr('data-filter'); 
        $('#'+parentul).isotope({ filter: selector }, function(){ });
        
        return(false);
    });
    
});